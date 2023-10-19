import base64
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
import io
import openai
import re
import ast
from jinja2 import contextfunction
import os
import boto3
from botocore.exceptions import ClientError
import json
import base64
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)

#log filename
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

def get_secret():

    secret_name = "open-api-key"
    region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    # Retrieve secret
    get_secret_value_response = client.get_secret_value(SecretId=secret_name)

    if 'SecretString' in get_secret_value_response:
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    else:
        decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
        return json.loads(decoded_binary_secret)
    
# Set OpenAI API key 
secrets = get_secret()
openai.api_key = secrets['OPEN_API_KEY']
app = FastAPI()

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Shared state
class SharedState:
    def __init__(self):
        self.template_table_info = None
        self.df_template = None
        self.ambiguous_columns = None
        self.table_a_info = None
        self.mapped_cols = None
        self.final_columns = None
        self.df = None
        self.resolved_columns = None

shared_state = SharedState()

####################

# Dependency
def get_shared_state():
    return shared_state

@app.get("/", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload_form.html", {"request": request})

@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...), state: SharedState = Depends(get_shared_state)):
    state.df_template = await read_file(file)
    state.template_table_info = extract_table_info(state.df_template)
    return RedirectResponse(url="/uploadfileA/", status_code=303)

@app.get("/uploadfileA/")
async def upload_form_a(request: Request, state: SharedState = Depends(get_shared_state)):
    if not state.template_table_info:
        raise HTTPException(status_code=400, detail="Template table not uploaded yet")
    return templates.TemplateResponse("upload_form_a.html", {"request": request})

@app.post("/uploadfileA/")
async def upload_fileA(file: UploadFile = File(...), state: SharedState = Depends(get_shared_state)):
    state.df = await read_file(file)
    state.table_a_info = extract_table_info(state.df)
    comparison_result, state.mapped_cols, state.ambiguous_columns = await compare_tables_with_openai(state.template_table_info, state.table_a_info, state)
    return resolve_ambiguity(state.mapped_cols, state)

@app.get("/resolve_ambiguous/", response_class=HTMLResponse)
async def resolve_ambiguous(request: Request, state: SharedState = Depends(get_shared_state)):
    if not state.ambiguous_columns:
        return {"message": "No ambiguous columns to resolve"}
    return templates.TemplateResponse(
        "resolve_ambiguous.html",
        {
            "request": request,
            "options": state.ambiguous_columns  # pass the ambiguous_columns dictionary to the template
        }
    )

@app.post("/resolve_ambiguous/")
async def resolve_ambiguous_post(request: Request, state: SharedState = Depends(get_shared_state)):
    form = await request.form()

    state.resolved_columns = state.mapped_cols.copy()
    for key, value in form.items():
        if key in state.ambiguous_columns:
            state.resolved_columns[key] = value

    # print(f"Resolved columns: {state.resolved_columns}\nRedirecting to show_code endpoint")
    logging.info(f"Resolved columns: {state.resolved_columns}\nRedirecting to show_code endpoint")
    return RedirectResponse(url="/show_code/", status_code=303)

@app.get("/show_code/")
async def show_code(request: Request, state: SharedState = Depends(get_shared_state)):
    code_snippet = generate_transformation_code(state)
    return templates.TemplateResponse("show_code.html", {"request": request, "code_snippet": code_snippet})

@app.post("/confirm_code/")
async def confirm_code(request: Request, state: SharedState = Depends(get_shared_state)):
    code_snippet = generate_transformation_code(state)
    try:

        # print("Table A columns before applying transformations:", state.df.columns.tolist())
        # print("Executing code snippet to transform table A to template table")
        logging.info(f"Table A columns before applying transformations: {state.df.columns.tolist()}")
        logging.info(f"Executing code snippet to transform table A to template table: {code_snippet}")

        exec_globals = {}
        exec_locals = {"df": state.df}

        try:
            exec(code_snippet, exec_globals, exec_locals)
            state.df = exec_locals['df']
            # print("Code snippet executed successfully.")
            logging.info("Code snippet executed successfully.")
        except Exception as e_inner:
            # print(f"Error executing code snippet: {str(e_inner)}")
            logging.error(f"Error executing code snippet: {str(e_inner)}")
            raise e_inner
        # print df columns after applying transformations
        # print("Table A columns after applying transformations:", state.df.columns.tolist())
        logging.info(f"Table A columns after applying transformations: {state.df.columns.tolist()}")

        # Save the final dataframe as a CSV file
        state.df.to_csv("final_table.csv", index=False)

        # Validation Checks here
        assert set(state.df.columns) == set(state.df_template.columns)
        for col in state.df.columns:
            assert state.df[col].dtype == state.df_template[col].dtype

        # print("Validation checks passed.")
        logging.info("Validation checks passed.")

        # Show the final DataFrame after applying transformations
        # print("Converting df to html table")
        logging.info("Converting df to html table")
        try:
            table = state.df.to_html(classes='table')
            # print("Converted df to html table successfully", table)
            logging.info(f"Converted df to html table successfully: {table}")
        except Exception as e:
            # print(f"Error converting df to html table: {str(e)}")
            logging.error(f"Error converting df to html table: {str(e)}")
            table = None
        return templates.TemplateResponse("confirm_code.html", {"request": request, "table": table})
    except Exception as e:
        return {"message": f"Error during transformations: {str(e)}"}
    

@app.get("/edit_code/")
async def edit_code(request: Request, state: SharedState = Depends(get_shared_state)):
    code_snippet = generate_transformation_code(state)
    return templates.TemplateResponse("edit_code.html", {"request": request, "code_snippet": code_snippet})

@app.post("/apply_edited_code/")
async def apply_edited_code(request: Request, state: SharedState = Depends(get_shared_state)):
    form = await request.form()
    edited_code = form.get("code")

    try:
        # Execute the edited code
        # print("Table A columns before applying transformations:", state.df.columns.tolist())
        logging.info(f"Table A columns before applying transformations: {state.df.columns.tolist()}")
        # print("Executing code snippet to transform table A to template table")
        logging.info(f"Executing code snippet to transform table A to template table:\n {edited_code}") 
        exec_globals = {}
        exec_locals = {"df": state.df}

        try:
            exec(edited_code, exec_globals, exec_locals)
            state.df = exec_locals['df']
            # print("Code snippet executed successfully.")
            logging.info("Code snippet executed successfully.")
        except Exception as e_inner:
            # print(f"Error executing code snippet: {str(e_inner)}")
            logging.error(f"Error executing code snippet: {str(e_inner)}")
            raise e_inner
        # print df columns after applying transformations
        # print("Table A columns after applying transformations:", state.df.columns.tolist())
        logging.info(f"Table A columns after applying transformations: {state.df.columns.tolist()}")

        # Save the final dataframe as a CSV file
        state.df.to_csv("final_table.csv", index=False)

        # Validation Checks here
        assert set(state.df.columns) == set(state.df_template.columns)
        for col in state.df.columns:
            assert state.df[col].dtype == state.df_template[col].dtype

        # print("Validation checks passed.")
        logging.info("Validation checks passed.")

        try:
            table = state.df.to_html(classes='table')
            # print("Converted df to html table successfully", table)
            logging.info(f"Converted df to html table successfully: {table}")
        except Exception as e:
            # print(f"Error converting df to html table: {str(e)}")
            logging.error(f"Error converting df to html table: {str(e)}")
            table = None
        return templates.TemplateResponse("apply_edited_code.html", {"request": request, "table": table})
    
    except Exception as e:
        return {"message": f"Error during transformations: {str(e)}"}
    
####################

async def read_file(file: UploadFile):
    file_bytes = await file.read()
    return pd.read_csv(io.BytesIO(file_bytes))

def extract_table_info(df: pd.DataFrame):
    return {
        "columns": df.columns.tolist(),
        "dtypes": df.dtypes.tolist(),
        "describe": df.describe().to_dict()
    }

def resolve_ambiguity(mapped_cols, state: SharedState):
    if state.ambiguous_columns:
        # print(f"Ambiguous columns found: {state.ambiguous_columns}\nRedirecting to resolve_ambiguous endpoint")
        logging.info(f"Ambiguous columns found: {state.ambiguous_columns}\nRedirecting to resolve_ambiguous endpoint")
        return RedirectResponse(url="/resolve_ambiguous/", status_code=303)
    else:
        # print(f"No ambiguous columns found. Returning comparison result")
        logging.info(f"No ambiguous columns found. Returning comparison result")
        final_columns = {key: value for key, value in mapped_cols.items() if key not in state.ambiguous_columns}
        return final_columns
    
def build_openai_prompt(info1, info2):
    """
    Builds a prompt for OpenAI's API to compare two tables based on certain attributes.
    
    Parameters:
    - info1 (dict): Information about the template table. 
                    Keys include 'columns', 'dtypes', and 'describe'.
    - info2 (dict): Information about table A. 
                    Keys include 'columns', 'dtypes', and 'describe'.

    Returns:
    - str: The formatted prompt for OpenAI's API.
    """

    general_instruction = """Determine an overall similarity score for each column in Template table when compared to the columns in the table A. 
    Identify and return as a key-value pair the most suitable mapping from Table A to the Template table columns.
    Take into consideration not just column name, but data type and data distribution for each column.
    Disregard any additional columns from Table A that don't have a corresponding match in the Template table.
    It is very important to check for ambiguous columns where there might be more than one column match with similar name or data.\n\n"""

    template_info = f"Template Table Information:\nColumns: {info1['columns']}\nData Types: {info1['dtypes']}\nSummary Stats: {info1['describe']}\n\n"
    
    table_a_info = f"Table A Information:\nColumns: {info2['columns']}\nData Types: {info2['dtypes']}\nSummary Stats: {info2['describe']}\n"

    mapping_instruction = """\n\nI want mapped columns in python key-value pair format as shown in example below:
    mapped_columns_dict={'column1': 'possible_match1', 'column2': 'possible_match2'}\n\n"""
    
    ambiguity_instruction = r"""Please also provide ambiguous columns in python key-value pair format as shown in example below:
    ambiguous_columns_dict={'column1': ['possible_match1', 'possible_match2'], 'column2': ['possible_match1', 'possible_match2', 'possible_match3']}
    \n\nThere should be at least two values for each key in ambiguous_columns_dict\n\n"""

    key_value_instruction = "Always the key is template table column name and value is table A column name\n"

    return general_instruction + template_info + table_a_info + mapping_instruction + ambiguity_instruction + key_value_instruction

# Function to parse the OpenAI API response
def parse_openai_response(response):
    analysis = response.choices[0].text.strip()
    matches = re.findall(r'\{(.*?)\}', analysis, re.DOTALL)
    return matches

# Function to filter and prepare the final result
def prepare_final_result(matches, state: SharedState = Depends(get_shared_state)):
    mapped_cols = {}
    state.ambiguous_columns = {}
    
    if matches and len(matches) >= 2:
        mapped_cols = ast.literal_eval("{" + matches[0] + "}")
        state.ambiguous_columns = ast.literal_eval("{" + matches[1] + "}")
    
    state.ambiguous_columns = {key: value for key, value in state.ambiguous_columns.items() if len(value) > 1}
    mapped_cols = {key: value for key, value in mapped_cols.items() if key not in state.ambiguous_columns}
    
    return mapped_cols, state.ambiguous_columns

# The main function
async def compare_tables_with_openai(info1, info2, state: SharedState = Depends(get_shared_state)):
    
    max_retries = 5
    retries = 0
    
    while retries < max_retries:
        prompt = build_openai_prompt(info1, info2)
        
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=400
        )
        
        matches = parse_openai_response(response)
        mapped_cols, state.ambiguous_columns = prepare_final_result(matches)
        
        if mapped_cols and state.ambiguous_columns:
            break
        
        retries += 1
    
    if retries == max_retries and (not mapped_cols or not state.ambiguous_columns):
        return "Max retries reached. No suitable mapping found.", {}, {}
    
    return None, mapped_cols, state.ambiguous_columns

def generate_transformation_code(state: SharedState):
    """
    Generates Python code for transforming Table A to align with the template table.
    
    Parameters:
    - resolved_columns (dict): Mapping between template table and Table A columns.
    - template_table_info (dict): Information about the template table. 
                                  Keys include 'columns' and 'dtypes'.
    - table_a_info (dict): Information about Table A. 
                           Keys include 'columns' and 'dtypes'.
    - df_template (DataFrame): The template table as a DataFrame.
    - df (DataFrame): Table A as a DataFrame.

    Returns:
    - str: Generated Python code for transforming Table A.
    """

    # Reverse the mapping to prepare for renaming Table A columns
    
    reversed_mapping = {value: key for key, value in state.resolved_columns.items()}
    
    # Initialize list to hold code snippets
    code_snippets = []
    
    # Code for Data Type Conversion
    code_snippets.append("\n# Convert data types of matching columns")
    for template_col, table_a_col in state.resolved_columns.items():
        template_dtype = state.template_table_info["dtypes"][state.template_table_info["columns"].index(template_col)]
        table_a_dtype = state.table_a_info["dtypes"][state.table_a_info["columns"].index(table_a_col)]
        if template_dtype != table_a_dtype:
            code_snippets.append(f"df['{table_a_col}'] = df['{table_a_col}'].astype('{template_dtype}')")
    
    # Code for Renaming Columns
    code_snippets.append("\n# Rename columns")
    code_snippets.append(f"df.rename(columns={reversed_mapping}, inplace=True)")

    # Code for Dropping Unnecessary Columns
    template_columns = state.df_template.columns.tolist()
    code_snippets.append("\n# Drop columns that are not in the template table")
    code_snippets.append(f"df.drop(columns=[col for col in df.columns if col not in {template_columns}], inplace=True)")
    
    # Code for Reordering Columns
    code_snippets.append("\n# Reorder columns")
    code_snippets.append(f"df = df[{template_columns}]")
    
    return '\n'.join(code_snippets)
# LLM Table Mapping Tool: README

## Project Overview

In the financial sector, it is common to have to map data from various Excel tables into a target format. This tool aims to streamline the process by using Language Models for Less (LLM) to perform these mappings automatically. This document outlines the task, the solution approach, and the expected result.

---

## Task Description

The primary task is to map tables A and B to a target template format by transferring and transforming values. The template table has the following columns:

- Date
- EmployeeName
- Plan
- PolicyNumber
- Premium

Example:
```
Date, EmployeeName, Plan, PolicyNumber, Premium
01-05-2023, John Doe, Gold, AB12345, 150
02-05-2023, Jane Smith, Silver, CD67890, 100
...
```

Example tables are attached as `.csv` files.

---

## Solution Approach

1. **Extract Column Info**: Retrieve meta information about the columns of the Template table and tables A and B.
   
2. **Find Similar Columns**: For tables A and B, utilize LLM to find columns that are similar to those in the Template table.

3. **Resolve Ambiguities**: If ambiguous mapping exists, prompt the user to select the most suitable column.

4. **Generate Mapping Code**: Generate code snippets or pseudocode to perform the data transformation. For example, convert date formats from `dd.mm.yyyy` to `mm.dd.yyyy`.

5. **Validation**: After transferring the data, validate that the transformation is correct. If errors are found, alert the user.

---

## Additional Challenge

- **Retraining**: Save transformation logic for future use and retrain the model on it. This is not required but would be a plus.

---

## Example User Journey

1. User uploads the Template table.
2. User uploads table A.
3. System suggests similar columns for each column in the Template, showing the rationale behind the suggestion.
4. User confirms the mapping.
5. System generates and displays transformation code. User can edit and run it.
6. User receives the transformed table in Template format.
7. Repeat the above steps for table B.

---
## Edge Cases

**Template Table**
1. Empty File or No Columns: Error if uploaded file is empty or lacks columns.
2. Invalid File Format: Error if a non-CSV file is uploaded.
3. Large File: Error if uploaded file exceeds allowable size.
4. Duplicate Column Names: Error if columns in template have the same name.
5. Special Characters in Column Names: Warning if column names include special characters.
6. Mixed Data Types: Warning if columns have mixed data types.

**Other Table**
1. No Overlap with Template: Error if no overlapping columns with the template.
2. Partial Overlap: Warning if only a subset of columns matches with the template.
3. More Columns than Template: Warning if the other table has additional columns.
4. Data Inconsistency: Warning if data does not conform to expected types or constraints.
5. Different Ordering of Columns: Warning if columns are not in the same order as the template.

**Common for Both**
1. Non-Tabular Data: Error if uploaded CSV does not form a valid table.
2. Null or Missing Values: Warning if null or missing values are present.
3. High Cardinality Columns: Warning for columns with high unique value counts.
4. Case Sensitivity: Warning for differing casing in column names between tables.

**GPT-3 Specific**
1. Ambiguity Resolution Failure: Warning if GPT-3 fails to resolve ambiguities.
2. Rate Limiting: Error if OpenAI API rate limit is exceeded.
3. Connectivity Issues: Error if unable to reach OpenAI API.

## Exception handling
1. To handle most LLM errors, we can return back to main page and ask user to start from beginning.
2. Most other errors also stem from LLM wrongly estimating column names etc., so redirecting to home page and starting over should fix majority of issues.
3. It is better to test and add custom exceptions and how to handle them separately

---

**To overcome these edge cases and make this code production ready, there are lot of validation mechanisms and alerts that can be set up**

---

## Retraining on ingested data
We can save user feedback and corresponding error and store all the columns and prepare data for the model

# Sample code:

**Synthesizing some data**
```
data = {'column1': [1, 2, 3, None, 5], 'column2': [None, 2, 3, 4, 5]}
df = pd.DataFrame(data)
```

**Simulated function that performs table transformation**
```
def transform_table(df):
    try:
        df['new_column'] = df['column1'] + df['column2']
    except Exception as e:
        # Log the error and the data
        error_data.append({"input_data": df.to_dict(), "error": str(e)})
        raise e
```

**Synthetic Error Logs and Human Feedback**
we could maintain logs of errors and human feedback like this:
```
error_data = []
feedback_data = [
    {"input_data": df[:2].to_dict(), "feedback": "Works well"},
    {"input_data": df[2:4].to_dict(), "feedback": "Fails sometimes"},
]
```

**Retraining the Model**
Once we have accumulated enough data and feedback, we could identify the common causes of errors. For instance, we could realize that errors frequently occur when there are missing values.

After this analysis, we could improve the table transformation function like this:

**Improved function**
```
def transform_table_v2(df):
    df['new_column'] = df['column1'].fillna(0) + df['column2'].fillna(0)
```

**FastAPI Integration**
In the FastAPI application, we can switch to this new function after it has been tested:

```
@app.post("/transform/")
async def transform(df: dict):
    df = pd.DataFrame(df)
    try:
        result = transform_table_v2(df)  # Using the new function
        return {"result": result.to_dict()}
    except Exception as e:
        return error_redirect(request)
```

This way, we have utilized logged error data and human feedback for improving the table transformation process.
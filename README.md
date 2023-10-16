# LLM Table Mapping Tool: README

## Project Overview

In the financial sector, it is common to have to map data from various Excel tables into a target format. This tool aims to streamline the process by using Language Models for Less (LLM) to perform these mappings automatically. This document outlines the task, the solution approach, and the expected result.

---

## Table of Contents

- [Task Description](#task-description)
- [Solution Approach](#solution-approach)
- [Additional Challenge](#additional-challenge)
- [Expected Result](#expected-result)
- [Example User Journey](#example-user-journey)
- [Edge Cases](#edge-cases)

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

## Expected Result

1. Source code hosted on GitHub, utilizing OpenAI API, Langchain, and other LLMOps tools.
2. A public domain interface for performing and testing these operations.

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

- **Mismatched Data Types**: Ensure that the data types in the columns match or can be converted.
- **Missing Values**: Handle NULL or missing values gracefully, either by skipping or using a default value.
- **Inconsistent Formatting**: The tool should be able to recognize and adapt to inconsistent data formats.

---

To overcome these edge cases, implementing a robust validation mechanism and offering customizable transformation options can be valuable.

--- 
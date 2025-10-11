# Data Directory

This directory contains the chatbot data file and other data files for the bank management system.

## Required Files

### BankBot_Data_Extended.xlsx
This Excel file should contain the following sheets:
- **Definitions**: Banking terms and definitions
- **DepositRates**: Current deposit interest rates
- **LoanRates**: Current loan interest rates  
- **BankInfo**: General bank information
- **Forms**: Available forms and documents

## File Structure
```
data/
├── BankBot_Data_Extended.xlsx  # Main chatbot data file
└── README.md                   # This file
```

## Note
Make sure to place the `BankBot_Data_Extended.xlsx` file in this directory before running the application. The chatbot will not function properly without this file.

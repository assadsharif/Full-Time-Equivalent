"""
Xero Accounting MCP Server — exposes Xero accounting tools via FastMCP (stdio transport).

Tools:
    xero_get_invoices           Get invoices with filters
    xero_get_expenses           Get expense claims and bills
    xero_get_balance_sheet      Get balance sheet summary
    xero_get_profit_loss        Get profit & loss statement
    xero_get_bank_transactions  Get bank transactions
    xero_get_contacts           Get customers and suppliers
    xero_create_invoice         Create new invoice (HITL approval required)
    xero_record_expense         Record new expense (HITL approval required)
    xero_get_tax_summary        Get tax/GST summary
    xero_get_cash_flow          Get cash flow statement

Requires:
    - Xero API credentials (OAuth 2.0)
    - Stored in OS keyring or environment variables
"""

import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("xero_accounting_mcp")

# ---------------------------------------------------------------------------
# Security & Configuration
# ---------------------------------------------------------------------------


def _load_credentials() -> dict[str, str]:
    """
    Load Xero credentials from environment or keyring.

    Expected environment variables:
    - XERO_CLIENT_ID: OAuth 2.0 client ID
    - XERO_CLIENT_SECRET: OAuth 2.0 client secret
    - XERO_TENANT_ID: Xero organization/tenant ID
    - XERO_ACCESS_TOKEN: Current access token

    Returns:
        Dictionary with credentials or error
    """
    client_id = os.getenv("XERO_CLIENT_ID")
    client_secret = os.getenv("XERO_CLIENT_SECRET")
    tenant_id = os.getenv("XERO_TENANT_ID")
    access_token = os.getenv("XERO_ACCESS_TOKEN")

    if not all([client_id, tenant_id, access_token]):
        return {
            "error": "Xero credentials not configured",
            "setup": "Set XERO_CLIENT_ID, XERO_CLIENT_SECRET, XERO_TENANT_ID, and XERO_ACCESS_TOKEN environment variables",
        }

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "tenant_id": tenant_id,
        "access_token": access_token,
    }


def _mock_currency_amount(amount: float, currency: str = "USD") -> dict:
    """Generate mock currency amount."""
    return {"amount": round(amount, 2), "currency": currency}


# ---------------------------------------------------------------------------
# Pydantic Input Models
# ---------------------------------------------------------------------------


class XeroGetInvoicesInput(BaseModel):
    """Input for xero_get_invoices."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    status: Optional[Literal["DRAFT", "SUBMITTED", "AUTHORISED", "PAID", "VOIDED"]] = (
        Field(None, description="Filter by invoice status")
    )
    contact_id: Optional[str] = Field(None, description="Filter by customer contact ID")
    from_date: Optional[str] = Field(
        None, description="Start date (ISO format: YYYY-MM-DD)"
    )
    to_date: Optional[str] = Field(
        None, description="End date (ISO format: YYYY-MM-DD)"
    )
    limit: int = Field(
        default=50, ge=1, le=100, description="Maximum number of invoices to retrieve"
    )


class XeroGetExpensesInput(BaseModel):
    """Input for xero_get_expenses."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    from_date: Optional[str] = Field(
        None, description="Start date (ISO format: YYYY-MM-DD)"
    )
    to_date: Optional[str] = Field(
        None, description="End date (ISO format: YYYY-MM-DD)"
    )
    status: Optional[Literal["SUBMITTED", "AUTHORISED", "PAID"]] = Field(
        None, description="Filter by expense status"
    )
    limit: int = Field(
        default=50, ge=1, le=100, description="Maximum number of expenses to retrieve"
    )


class XeroGetBalanceSheetInput(BaseModel):
    """Input for xero_get_balance_sheet."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    date: Optional[str] = Field(
        None,
        description="Balance sheet date (ISO format: YYYY-MM-DD). Defaults to today.",
    )


class XeroGetProfitLossInput(BaseModel):
    """Input for xero_get_profit_loss."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    from_date: Optional[str] = Field(
        None, description="Start date (ISO format: YYYY-MM-DD)"
    )
    to_date: Optional[str] = Field(
        None, description="End date (ISO format: YYYY-MM-DD)"
    )
    periods: int = Field(
        default=1, ge=1, le=12, description="Number of periods to retrieve"
    )


class XeroGetBankTransactionsInput(BaseModel):
    """Input for xero_get_bank_transactions."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    bank_account_id: Optional[str] = Field(
        None, description="Specific bank account ID (defaults to all accounts)"
    )
    from_date: Optional[str] = Field(
        None, description="Start date (ISO format: YYYY-MM-DD)"
    )
    to_date: Optional[str] = Field(
        None, description="End date (ISO format: YYYY-MM-DD)"
    )
    limit: int = Field(
        default=100, ge=1, le=500, description="Maximum number of transactions"
    )


class XeroGetContactsInput(BaseModel):
    """Input for xero_get_contacts."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    contact_type: Optional[Literal["CUSTOMER", "SUPPLIER", "ALL"]] = Field(
        default="ALL", description="Type of contacts to retrieve"
    )
    limit: int = Field(
        default=50, ge=1, le=100, description="Maximum number of contacts"
    )


class XeroCreateInvoiceInput(BaseModel):
    """Input for xero_create_invoice."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    contact_id: str = Field(..., min_length=1, description="Customer contact ID")
    invoice_number: Optional[str] = Field(
        None, description="Invoice number (auto-generated if not provided)"
    )
    date: str = Field(..., description="Invoice date (ISO format: YYYY-MM-DD)")
    due_date: str = Field(..., description="Due date (ISO format: YYYY-MM-DD)")
    line_items: list[dict] = Field(
        ...,
        min_length=1,
        description="Invoice line items (description, quantity, unit_amount, account_code)",
    )
    reference: Optional[str] = Field(None, description="Invoice reference/notes")


class XeroRecordExpenseInput(BaseModel):
    """Input for xero_record_expense."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    date: str = Field(..., description="Expense date (ISO format: YYYY-MM-DD)")
    amount: float = Field(..., gt=0, description="Expense amount")
    description: str = Field(
        ..., min_length=1, max_length=500, description="Expense description"
    )
    account_code: str = Field(..., description="Account code for expense category")
    supplier_id: Optional[str] = Field(None, description="Supplier contact ID")
    reference: Optional[str] = Field(
        None, description="Expense reference/receipt number"
    )


class XeroGetTaxSummaryInput(BaseModel):
    """Input for xero_get_tax_summary."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    from_date: Optional[str] = Field(
        None, description="Start date (ISO format: YYYY-MM-DD)"
    )
    to_date: Optional[str] = Field(
        None, description="End date (ISO format: YYYY-MM-DD)"
    )


class XeroGetCashFlowInput(BaseModel):
    """Input for xero_get_cash_flow."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    from_date: Optional[str] = Field(
        None, description="Start date (ISO format: YYYY-MM-DD)"
    )
    to_date: Optional[str] = Field(
        None, description="End date (ISO format: YYYY-MM-DD)"
    )


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def xero_get_invoices(input: XeroGetInvoicesInput) -> dict:
    """
    Get invoices from Xero with optional filters.

    Retrieves invoices filtered by status, contact, or date range.
    Useful for accounts receivable tracking and reporting.

    Returns:
        List of invoices with details and amounts
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    # Mock data
    mock_invoices = [
        {
            "invoice_id": f"INV-{1000 + i}",
            "invoice_number": f"INV-{1000 + i}",
            "contact": f"Customer {i}",
            "date": (datetime.now() - timedelta(days=i * 7)).strftime("%Y-%m-%d"),
            "due_date": (datetime.now() - timedelta(days=i * 7 - 30)).strftime(
                "%Y-%m-%d"
            ),
            "status": "PAID" if i % 2 == 0 else "AUTHORISED",
            "total": _mock_currency_amount(1000 + i * 250),
            "amount_due": _mock_currency_amount(0 if i % 2 == 0 else 1000 + i * 250),
        }
        for i in range(1, min(input.limit, 10) + 1)
    ]

    return {
        "success": True,
        "invoices": mock_invoices,
        "count": len(mock_invoices),
        "filters_applied": {
            "status": input.status,
            "contact_id": input.contact_id,
            "from_date": input.from_date,
            "to_date": input.to_date,
        },
        "mock_mode": True,
        "note": "TODO: Implement actual Xero API integration with OAuth 2.0",
    }


@mcp.tool()
def xero_get_expenses(input: XeroGetExpensesInput) -> dict:
    """
    Get expenses and bills from Xero.

    Retrieves expense claims and bills for accounts payable tracking.

    Returns:
        List of expenses with amounts and statuses
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    mock_expenses = [
        {
            "expense_id": f"EXP-{2000 + i}",
            "date": (datetime.now() - timedelta(days=i * 3)).strftime("%Y-%m-%d"),
            "description": f"Business expense {i}",
            "supplier": f"Supplier {i}",
            "category": "Office Expenses" if i % 2 == 0 else "Travel",
            "amount": _mock_currency_amount(50 + i * 25),
            "status": "PAID" if i % 3 == 0 else "AUTHORISED",
        }
        for i in range(1, min(input.limit, 10) + 1)
    ]

    return {
        "success": True,
        "expenses": mock_expenses,
        "count": len(mock_expenses),
        "total_amount": _mock_currency_amount(
            sum(e["amount"]["amount"] for e in mock_expenses)
        ),
        "mock_mode": True,
        "note": "TODO: Implement actual Xero API integration",
    }


@mcp.tool()
def xero_get_balance_sheet(input: XeroGetBalanceSheetInput) -> dict:
    """
    Get balance sheet summary from Xero.

    Retrieves current assets, liabilities, and equity.
    Essential for financial health monitoring.

    Returns:
        Balance sheet with assets, liabilities, and equity
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    date = input.date or datetime.now().strftime("%Y-%m-%d")

    return {
        "success": True,
        "as_of_date": date,
        "balance_sheet": {
            "assets": {
                "current_assets": {
                    "bank": _mock_currency_amount(50000),
                    "accounts_receivable": _mock_currency_amount(25000),
                    "inventory": _mock_currency_amount(15000),
                    "total": _mock_currency_amount(90000),
                },
                "fixed_assets": {
                    "equipment": _mock_currency_amount(30000),
                    "vehicles": _mock_currency_amount(20000),
                    "total": _mock_currency_amount(50000),
                },
                "total_assets": _mock_currency_amount(140000),
            },
            "liabilities": {
                "current_liabilities": {
                    "accounts_payable": _mock_currency_amount(15000),
                    "short_term_loans": _mock_currency_amount(10000),
                    "total": _mock_currency_amount(25000),
                },
                "long_term_liabilities": {
                    "long_term_loans": _mock_currency_amount(40000),
                    "total": _mock_currency_amount(40000),
                },
                "total_liabilities": _mock_currency_amount(65000),
            },
            "equity": {
                "retained_earnings": _mock_currency_amount(60000),
                "current_year_earnings": _mock_currency_amount(15000),
                "total_equity": _mock_currency_amount(75000),
            },
        },
        "mock_mode": True,
        "note": "TODO: Implement actual Xero API integration",
    }


@mcp.tool()
def xero_get_profit_loss(input: XeroGetProfitLossInput) -> dict:
    """
    Get profit & loss statement from Xero.

    Retrieves income, expenses, and net profit for specified period.
    Critical for CEO briefing financial section.

    Returns:
        P&L statement with revenue, expenses, and profit
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    return {
        "success": True,
        "period": {
            "from_date": input.from_date
            or (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "to_date": input.to_date or datetime.now().strftime("%Y-%m-%d"),
        },
        "profit_loss": {
            "income": {
                "sales_revenue": _mock_currency_amount(85000),
                "other_income": _mock_currency_amount(5000),
                "total_income": _mock_currency_amount(90000),
            },
            "cost_of_goods_sold": {
                "materials": _mock_currency_amount(25000),
                "labor": _mock_currency_amount(15000),
                "total_cogs": _mock_currency_amount(40000),
            },
            "gross_profit": _mock_currency_amount(50000),
            "operating_expenses": {
                "salaries": _mock_currency_amount(20000),
                "rent": _mock_currency_amount(5000),
                "utilities": _mock_currency_amount(2000),
                "marketing": _mock_currency_amount(3000),
                "other": _mock_currency_amount(5000),
                "total_operating_expenses": _mock_currency_amount(35000),
            },
            "operating_profit": _mock_currency_amount(15000),
            "other_expenses": {
                "interest": _mock_currency_amount(1000),
                "total": _mock_currency_amount(1000),
            },
            "net_profit": _mock_currency_amount(14000),
            "net_profit_margin": 0.156,  # 15.6%
        },
        "mock_mode": True,
        "note": "TODO: Implement actual Xero API integration",
    }


@mcp.tool()
def xero_get_bank_transactions(input: XeroGetBankTransactionsInput) -> dict:
    """
    Get bank transactions from Xero.

    Retrieves bank transactions for reconciliation and cash tracking.

    Returns:
        List of bank transactions with amounts and categories
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    mock_transactions = [
        {
            "transaction_id": f"TXN-{i}",
            "date": (datetime.now() - timedelta(days=i * 2)).strftime("%Y-%m-%d"),
            "description": f"Transaction {i}",
            "type": "RECEIVE" if i % 2 == 0 else "SPEND",
            "amount": _mock_currency_amount((1 if i % 2 == 0 else -1) * (100 + i * 50)),
            "category": "Sales" if i % 2 == 0 else "Expenses",
            "reconciled": i % 3 == 0,
        }
        for i in range(1, min(input.limit, 10) + 1)
    ]

    return {
        "success": True,
        "transactions": mock_transactions,
        "count": len(mock_transactions),
        "bank_account": input.bank_account_id or "ALL_ACCOUNTS",
        "mock_mode": True,
        "note": "TODO: Implement actual Xero API integration",
    }


@mcp.tool()
def xero_get_contacts(input: XeroGetContactsInput) -> dict:
    """
    Get customers and suppliers from Xero.

    Retrieves contact list for invoicing and expense tracking.

    Returns:
        List of contacts with names and IDs
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    mock_contacts = [
        {
            "contact_id": f"CONT-{i}",
            "name": f"{'Customer' if i % 2 == 0 else 'Supplier'} {i}",
            "type": "CUSTOMER" if i % 2 == 0 else "SUPPLIER",
            "email": f"contact{i}@example.com",
            "phone": f"+1-555-{1000+i}",
        }
        for i in range(1, min(input.limit, 10) + 1)
    ]

    if input.contact_type != "ALL":
        mock_contacts = [c for c in mock_contacts if c["type"] == input.contact_type]

    return {
        "success": True,
        "contacts": mock_contacts,
        "count": len(mock_contacts),
        "contact_type": input.contact_type,
        "mock_mode": True,
        "note": "TODO: Implement actual Xero API integration",
    }


@mcp.tool()
def xero_create_invoice(input: XeroCreateInvoiceInput) -> dict:
    """
    Create new invoice in Xero.

    Creates a draft invoice. Requires HITL approval before submitting to Xero.

    Returns:
        Invoice creation status and preview
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    total_amount = sum(
        item.get("quantity", 1) * item.get("unit_amount", 0)
        for item in input.line_items
    )

    return {
        "success": True,
        "status": "pending_approval",
        "invoice_preview": {
            "contact_id": input.contact_id,
            "invoice_number": input.invoice_number
            or f"INV-{datetime.now().strftime('%Y%m%d')}",
            "date": input.date,
            "due_date": input.due_date,
            "line_items": input.line_items,
            "reference": input.reference,
            "total": _mock_currency_amount(total_amount),
        },
        "approval_required": True,
        "message": "Invoice queued for approval. Move to /Approved to submit to Xero.",
        "mock_mode": True,
        "note": "TODO: Implement actual Xero API integration",
    }


@mcp.tool()
def xero_record_expense(input: XeroRecordExpenseInput) -> dict:
    """
    Record new expense in Xero.

    Creates an expense record. Requires HITL approval before submitting to Xero.

    Returns:
        Expense recording status and preview
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    return {
        "success": True,
        "status": "pending_approval",
        "expense_preview": {
            "date": input.date,
            "amount": _mock_currency_amount(input.amount),
            "description": input.description,
            "account_code": input.account_code,
            "supplier_id": input.supplier_id,
            "reference": input.reference,
        },
        "approval_required": True,
        "message": "Expense queued for approval. Move to /Approved to submit to Xero.",
        "mock_mode": True,
        "note": "TODO: Implement actual Xero API integration",
    }


@mcp.tool()
def xero_get_tax_summary(input: XeroGetTaxSummaryInput) -> dict:
    """
    Get tax/GST summary from Xero.

    Retrieves tax collected and paid for tax reporting.

    Returns:
        Tax summary with collections and payments
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    return {
        "success": True,
        "period": {
            "from_date": input.from_date
            or (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
            "to_date": input.to_date or datetime.now().strftime("%Y-%m-%d"),
        },
        "tax_summary": {
            "sales_tax_collected": _mock_currency_amount(9000),
            "purchase_tax_paid": _mock_currency_amount(4000),
            "net_tax_due": _mock_currency_amount(5000),
        },
        "mock_mode": True,
        "note": "TODO: Implement actual Xero API integration",
    }


@mcp.tool()
def xero_get_cash_flow(input: XeroGetCashFlowInput) -> dict:
    """
    Get cash flow statement from Xero.

    Retrieves cash inflows and outflows for cash management.

    Returns:
        Cash flow statement with operating, investing, and financing activities
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    return {
        "success": True,
        "period": {
            "from_date": input.from_date
            or (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "to_date": input.to_date or datetime.now().strftime("%Y-%m-%d"),
        },
        "cash_flow": {
            "operating_activities": {
                "cash_from_customers": _mock_currency_amount(80000),
                "cash_to_suppliers": _mock_currency_amount(-35000),
                "cash_to_employees": _mock_currency_amount(-20000),
                "net_operating_cash": _mock_currency_amount(25000),
            },
            "investing_activities": {
                "equipment_purchases": _mock_currency_amount(-10000),
                "net_investing_cash": _mock_currency_amount(-10000),
            },
            "financing_activities": {
                "loan_proceeds": _mock_currency_amount(0),
                "loan_repayments": _mock_currency_amount(-5000),
                "net_financing_cash": _mock_currency_amount(-5000),
            },
            "net_cash_flow": _mock_currency_amount(10000),
            "opening_cash_balance": _mock_currency_amount(40000),
            "closing_cash_balance": _mock_currency_amount(50000),
        },
        "mock_mode": True,
        "note": "TODO: Implement actual Xero API integration",
    }


# ---------------------------------------------------------------------------
# Server Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")

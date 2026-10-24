"""Pure legal and integrity logic (ARCHITECTURE.md Section 3.2).

Modules in this package perform no I/O, read no clock and no environment. "Today" and all
facts are passed in by callers. Legal dates are Asia/Kolkata calendar dates (`datetime.date`);
money is `decimal.Decimal` in rupees with at most two decimal places (ADR-012).
"""

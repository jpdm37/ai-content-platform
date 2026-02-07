#!/bin/bash

echo ""
echo "============================================================"
echo "   AI Content Platform - Setup Wizard"
echo "============================================================"
echo ""
echo "This wizard will help you deploy your AI Content Platform."
echo ""

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "ERROR: Python is not installed!"
    echo ""
    echo "Please install Python:"
    echo "  macOS: brew install python3"
    echo "  Ubuntu: sudo apt install python3"
    echo ""
    exit 1
fi

echo "Python found: $($PYTHON --version)"
echo ""
echo "Starting setup wizard..."
echo ""

$PYTHON setup-wizard.py

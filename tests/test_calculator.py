# """ tests/test_calculator.py """
# import sys
# import pytest
# from io import StringIO
# from app.calculator import display_help, display_history, calculator

import datetime
from pathlib import Path
import pandas as pd
import pytest
from unittest.mock import Mock, patch, PropertyMock
from decimal import Decimal
from tempfile import TemporaryDirectory
from app.calculator import Calculator
from app.calculator_repl import calculator_repl
from app.calculator_config import CalculatorConfig
from app.exceptions import OperationError, ValidationError
from app.history import LoggingObserver, AutoSaveObserver
from app.operations import OperationFactory

# Fixture to initialize Calculator with a temporary directory for file paths
@pytest.fixture
def calculator():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config = CalculatorConfig(base_dir=temp_path)

        # Patch properties to use the temporary directory paths
        with patch.object(CalculatorConfig, 'log_dir', new_callable=PropertyMock) as mock_log_dir, \
             patch.object(CalculatorConfig, 'log_file', new_callable=PropertyMock) as mock_log_file, \
             patch.object(CalculatorConfig, 'history_dir', new_callable=PropertyMock) as mock_history_dir, \
             patch.object(CalculatorConfig, 'history_file', new_callable=PropertyMock) as mock_history_file:
            
            # Set return values to use paths within the temporary directory
            mock_log_dir.return_value = temp_path / "logs"
            mock_log_file.return_value = temp_path / "logs/calculator.log"
            mock_history_dir.return_value = temp_path / "history"
            mock_history_file.return_value = temp_path / "history/calculator_history.csv"
            
            # Return an instance of Calculator with the mocked config
            yield Calculator(config=config)

# Test Calculator Initialization

def test_calculator_initialization(calculator):
    assert calculator.history == []
    assert calculator.undo_stack == []
    assert calculator.redo_stack == []
    assert calculator.operation_strategy is None

# Test Logging Setup

@patch('app.calculator.logging.info')
def test_logging_setup(logging_info_mock):
    with patch.object(CalculatorConfig, 'log_dir', new_callable=PropertyMock) as mock_log_dir, \
         patch.object(CalculatorConfig, 'log_file', new_callable=PropertyMock) as mock_log_file:
        mock_log_dir.return_value = Path('/tmp/logs')
        mock_log_file.return_value = Path('/tmp/logs/calculator.log')
        
        # Instantiate calculator to trigger logging
        calculator = Calculator(CalculatorConfig())
        logging_info_mock.assert_any_call("Calculator initialized with configuration")

# Test Adding and Removing Observers

def test_add_observer(calculator):
    observer = LoggingObserver()
    calculator.add_observer(observer)
    assert observer in calculator.observers

def test_remove_observer(calculator):
    observer = LoggingObserver()
    calculator.add_observer(observer)
    calculator.remove_observer(observer)
    assert observer not in calculator.observers

# Test Setting Operations

def test_set_operation(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    assert calculator.operation_strategy == operation

# Test Performing Operations

def test_perform_operation_addition(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    result = calculator.perform_operation(2, 3)
    assert result == Decimal('5')

def test_perform_operation_validation_error(calculator):
    calculator.set_operation(OperationFactory.create_operation('add'))
    with pytest.raises(ValidationError):
        calculator.perform_operation('invalid', 3)

def test_perform_operation_operation_error(calculator):
    with pytest.raises(OperationError, match="No operation set"):
        calculator.perform_operation(2, 3)

# Test Undo/Redo Functionality

def test_undo(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.undo()
    assert calculator.history == []

def test_redo(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.undo()
    calculator.redo()
    assert len(calculator.history) == 1

# Test History Management

@patch('app.calculator.pd.DataFrame.to_csv')
def test_save_history(mock_to_csv, calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.save_history()
    mock_to_csv.assert_called_once()

@patch('app.calculator.pd.read_csv')
@patch('app.calculator.Path.exists', return_value=True)
def test_load_history(mock_exists, mock_read_csv, calculator):
    # Mock CSV data to match the expected format in from_dict
    mock_read_csv.return_value = pd.DataFrame({
        'operation': ['Addition'],
        'operand1': ['2'],
        'operand2': ['3'],
        'result': ['5'],
        'timestamp': [datetime.datetime.now().isoformat()]
    })
    
    # Test the load_history functionality
    try:
        calculator.load_history()
        # Verify history length after loading
        assert len(calculator.history) == 1
        # Verify the loaded values
        assert calculator.history[0].operation == "Addition"
        assert calculator.history[0].operand1 == Decimal("2")
        assert calculator.history[0].operand2 == Decimal("3")
        assert calculator.history[0].result == Decimal("5")
    except OperationError:
        pytest.fail("Loading history failed due to OperationError")
        
            
# Test Clearing History

def test_clear_history(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.clear_history()
    assert calculator.history == []
    assert calculator.undo_stack == []
    assert calculator.redo_stack == []

# Test REPL Commands (using patches for input/output handling)

@patch('builtins.input', side_effect=['exit'])
@patch('builtins.print')
def test_calculator_repl_exit(mock_print, mock_input):
    with patch('app.calculator.Calculator.save_history') as mock_save_history:
        calculator_repl()
        mock_save_history.assert_called_once()
        mock_print.assert_any_call("History saved successfully.")
        mock_print.assert_any_call("Goodbye!")

@patch('builtins.input', side_effect=['help', 'exit'])
@patch('builtins.print')
def test_calculator_repl_help(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("\nAvailable commands:")

@patch('builtins.input', side_effect=['add', '2', '3', 'exit'])
@patch('builtins.print')
def test_calculator_repl_addition(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("\nResult: 5")

def test_history_empty(monkeypatch, capsys):
    inputs = iter(["clear","history", "exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    calculator_repl()

    captured = capsys.readouterr()

    assert "No calculations in history" in captured.out

# def test_display_help(capsys):
#     """ 
#     Tests to ensure that the correct help message is displayed.
#     """
#     display_help()
#     captured = capsys.readouterr()
#     expected_output = """
#     REPL Calculator Help
#     --------------------
#     In order to use the REPL calculator: input <operation> <num1> <num2> to perform a specific operation with 2 numbers 
    
#     Supported operations include: 
#     - add
#     - subtract (note: this subtracts the second number from the first)
#     - multiply
#     - divide (note: this divides the first number by the second)

#     Some special commands that could be helpful: 
#     - help : Displays this help message
#     - history : Shows your history of calculations 
#     - exit : Exits the calculator 

#     Example operations: 
#     add 1 1 
#     subtract 5 3
#     multiply 2 4
#     divide 10 2
#     """
#     assert captured.out.strip() == expected_output.strip()

# def test_display_history_empty(capsys):
#     """Test to ensure that the correct message is displayed when history is empty."""
#     history = []
#     display_history(history)
#     captured = capsys.readouterr()
#     assert captured.out.strip() == "No calculations have been performed yet."

# def test_display_history(capsys):
#     """Test to ensure that the correct calculation history is displayed."""
#     history = ["addition: 1.0 add 1.0 = 2.0",
#                 "subtraction: 5.0 subtract 2.0 = 3.0",
#                 "multiplication: 2.0 multiply 4.0 = 8.0",
#                 "division: 10.0 divide 2.0 = 5.0"]
#     display_history(history)
#     captured = capsys.readouterr()
#     expected_output = """Calculation History:
# 1. addition: 1.0 add 1.0 = 2.0
# 2. subtraction: 5.0 subtract 2.0 = 3.0
# 3. multiplication: 2.0 multiply 4.0 = 8.0
# 4. division: 10.0 divide 2.0 = 5.0
#     """
#     assert captured.out.strip() == expected_output.strip()

# def test_exit(monkeypatch, capsys):
#     """Test the exit command in REPL."""
#     user_input= "exit\n"
#     monkeypatch.setattr('sys.stdin', StringIO(user_input))
#     with pytest.raises(SystemExit) as exc_info:
#         calculator()
#     captured = capsys.readouterr()
#     assert "Exiting calculator now... Thank you!" in captured.out
#     assert exc_info.type == SystemExit
#     assert exc_info.value.code == 0

# def test_calculator_help_command(monkeypatch,capsys):
#     """Test the help command in REPL."""
#     user_input= "help\nexit\n"
#     monkeypatch.setattr('sys.stdin', StringIO(user_input))
#     with pytest.raises(SystemExit) as exc_info:
#         calculator()
#     captured = capsys.readouterr()
#     assert "REPL Calculator Help" in captured.out
#     assert "Exiting calculator now... Thank you!" in captured.out

# def test_invalid_input(monkeypatch,capsys):
#     """Test invalid input in REPL."""
#     user_input = "invalid input\nadd 1\nsubtract 5\nexist\n"
#     monkeypatch.setattr('sys.stdin', StringIO(user_input))
#     with pytest.raises(SystemExit) as exc_info:
#         calculator()
#     captured = capsys.readouterr()
#     assert "Invalid input. Please follow the format: <operation> <num1> <num2>" in captured.out
#     assert "Type 'help' for more instructions!" in captured.out

# # Helper function to capture print statements
# def run_calculator_with_input(monkeypatch, inputs):
#     """
#     Simulates user input and captures output from the calculator REPL.
    
#     :param monkeypatch: pytest fixture to simulate user input
#     :param inputs: list of inputs to simulate
#     :return: captured output as a string
#     """
#     input_iterator = iter(inputs)
#     monkeypatch.setattr('builtins.input', lambda _: next(input_iterator))

#     # Capture the output of the calculator
#     #captured_output = StringIO()
#     #sys.stdout = captured_output
#     #calculator()
#     #sys.stdout = sys.__stdout__  # Reset stdout
#     #return captured_output.getvalue()

# # Positive Tests
# def test_addition(monkeypatch, capsys):
#     """Test addition operation in REPL."""
#     #inputs = ["add 2 3", "exit"]
#     #output = run_calculator_with_input(monkeypatch, inputs)
#     #assert "Result: 5.0" in output
#     user_input = "add 1 1\nexit\n"
#     monkeypatch.setattr('sys.stdin', StringIO(user_input))
#     with pytest.raises(SystemExit):
#         calculator()
#     captured = capsys.readouterr()
#     assert "Result: AddCalculation: 1.0 Add 1.0 = 2.0" in captured.out

# def test_subtraction(monkeypatch, capsys):
#     """Test subtraction operation in REPL."""
#     #inputs = ["subtract 5 2", "exit"]
#     #output = run_calculator_with_input(monkeypatch, inputs)
#     #assert "Result: 3.0" in output
#     user_input = "subtract 5 2\nexit\n"
#     monkeypatch.setattr('sys.stdin', StringIO(user_input))
#     with pytest.raises(SystemExit):
#         calculator()
#     captured = capsys.readouterr()
#     assert "Result: SubtractCalculation: 5.0 Subtract 2.0 = 3.0" in captured.out

# def test_multiplication(monkeypatch, capsys):
#     """Test multiplication operation in REPL."""
#     #inputs = ["multiply 4 5", "exit"]
#     #output = run_calculator_with_input(monkeypatch, inputs)
#     #assert "Result: 20.0" in output
#     user_input = "multiply 2 4\nexit\n"
#     monkeypatch.setattr('sys.stdin', StringIO(user_input))
#     with pytest.raises(SystemExit):
#         calculator()
#     captured = capsys.readouterr()
#     assert "Result: MultiplyCalculation: 2.0 Multiply 4.0 = 8.0" in captured.out

# def test_division(monkeypatch, capsys):
#     """Test division operation in REPL."""
#     #inputs = ["divide 10 2", "exit"]
#     #output = run_calculator_with_input(monkeypatch, inputs)
#     #assert "Result: 5.0" in output
#     user_input = "divide 10 2\nexit\n"
#     monkeypatch.setattr('sys.stdin', StringIO(user_input))
#     with pytest.raises(SystemExit):
#         calculator()
#     captured = capsys.readouterr()
#     assert "Result: DivideCalculation: 10.0 Divide 2.0 = 5.0" in captured.out

# # Negative Tests
# def test_invalid_operation(monkeypatch, capsys):
#     """Test invalid operation in REPL."""
#     #inputs = ["modulus 5 3", "exit"]
#     #output = run_calculator_with_input(monkeypatch, inputs)
#     #assert "Unknown operation" in output
#     user_input = "modulus 5 3\nexit\n"
#     monkeypatch.setattr('sys.stdin', StringIO(user_input))
#     with pytest.raises(SystemExit):
#         calculator()
#     captured = capsys.readouterr()
#     assert "Unsupported calculation type: 'modulus'. Available types: add, subtract, multiply, divide" in captured.out
#     assert "Type 'help' for more instructions and the list of supported operations!" in captured.out

# def test_invalid_input_format(monkeypatch, capsys):
#     """Test invalid input format in REPL."""
#     #inputs = ["add two three", "exit"]
#     #output = run_calculator_with_input(monkeypatch, inputs)
#     #assert "Invalid input. Please follow the format" in output
#     user_input = "add two three\nexit\n"
#     monkeypatch.setattr('sys.stdin', StringIO(user_input))
#     with pytest.raises(SystemExit):
#         calculator()
#     captured = capsys.readouterr()
#     assert "Invalid input. Please follow the format: <operation> <num1> <num2>" in captured.out or \
#            "could not convert string to float: 'two'" in captured.out

# def test_division_by_zero(monkeypatch, capsys):
#     """Test division by zero in REPL."""
#     #inputs = ["divide 5 0", "exit"]
#     #output = run_calculator_with_input(monkeypatch, inputs)
#     #assert "Division by zero is not allowed" in output
#     user_input = "divide 5 0\nexit\n"
#     monkeypatch.setattr('sys.stdin', StringIO(user_input))
#     with pytest.raises(SystemExit):
#         calculator()
#     captured = capsys.readouterr()
#     assert "Division by zero is not allowed" in captured.out

# def test_history(monkeypatch, capsys):
#     """Test history functionality in REPL."""
#     user_input = "add 1 1\nhistory\nexit\n"
#     monkeypatch.setattr('sys.stdin', StringIO(user_input))
#     with pytest.raises(SystemExit):
#         calculator()
#     captured = capsys.readouterr()
#     assert "Result: AddCalculation: 1.0 Add 1.0 = 2.0" in captured.out
#     assert "Calculation History:" in captured.out
#     assert "1. AddCalculation: 1.0 Add 1.0 = 2.0" in captured.out

# def test_calculator_keyboard_interrupt(monkeypatch, capsys):
#     """
#     Test the calculator's handling of KeyboardInterrupt (Ctrl+C)."""
#     def mock_input(prompt):
#         raise KeyboardInterrupt()
#     monkeypatch.setattr('builtins.input', mock_input)
#     with pytest.raises(SystemExit) as exc_info:
#         calculator()
#     captured = capsys.readouterr()
#     assert "\nKeyboard interrupt detected. Exiting calculator. Goodbye!" in captured.out
#     assert exc_info.value.code == 0

# def test_calculator_eof_error(monkeypatch, capsys):
#     """
#     Test the calculator's handling of EOFError (Ctrl+D). """    
#     def mock_input(prompt):
#         raise EOFError()
#     monkeypatch.setattr('builtins.input', mock_input)
#     with pytest.raises(SystemExit) as exc_info:
#         calculator()
#     captured = capsys.readouterr()
#     assert "\nEOF detected. Exiting calculator. Goodbye!" in captured.out
#     assert exc_info.value.code == 0

# def test_calculator_unexpected_exception(monkeypatch, capsys):
#     """
#     Test the calculator's handling of unexpected exceptions during calculation execution. """
#     class MockCalculation:
#         def execute(self):
#             raise Exception("Mock exception during execution")
#         def __str__(self):
#             return "MockCalculation"
#     def mock_create_calculation(operation, a, b):
#         return MockCalculation()
#     monkeypatch.setattr('app.calculation.CalculationFactory.create_calculation', mock_create_calculation)
#     user_input = 'add 10 5\nexit\n'
#     monkeypatch.setattr('sys.stdin', StringIO(user_input))
#     with pytest.raises(SystemExit):
#         calculator()
#     captured = capsys.readouterr()
#     assert "An error has occurred during calculation: Mock exception during execution" in captured.out
#     assert "Please try again!" in captured.out
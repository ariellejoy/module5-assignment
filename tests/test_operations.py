# import pytest
# from typing import Union  #this allows for multiple data types
# from app.operations import Operations

import pytest
from decimal import Decimal
from typing import Any, Dict, Type

from app.exceptions import ValidationError
from app.operations import (
    Operations,
    Addition,
    Subtraction,
    Multiplication,
    Division,
    Power,
    Root,
    OperationFactory,
)


class TestOperation:
    """Test base Operation class functionality."""

    def test_str_representation(self):
        """Test that string representation returns class name."""
        class TestOp(Operations):
            def execute(self, a: Decimal, b: Decimal) -> Decimal:
                return a

        assert str(TestOp()) == "TestOp"


class BaseOperationTest:
    """Base test class for all operations."""

    operation_class: Type[Operations]
    valid_test_cases: Dict[str, Dict[str, Any]]
    invalid_test_cases: Dict[str, Dict[str, Any]]

    def test_valid_operations(self):
        """Test operation with valid inputs."""
        operation = self.operation_class()
        for name, case in self.valid_test_cases.items():
            a = Decimal(str(case["a"]))
            b = Decimal(str(case["b"]))
            expected = Decimal(str(case["expected"]))
            result = operation.execute(a, b)
            assert result == expected, f"Failed case: {name}"

    def test_invalid_operations(self):
        """Test operation with invalid inputs raises appropriate errors."""
        operation = self.operation_class()
        for name, case in self.invalid_test_cases.items():
            a = Decimal(str(case["a"]))
            b = Decimal(str(case["b"]))
            error = case.get("error", ValidationError)
            error_message = case.get("message", "")

            with pytest.raises(error, match=error_message):
                operation.execute(a, b)


class TestAddition(BaseOperationTest):
    """Test Addition operation."""

    operation_class = Addition
    valid_test_cases = {
        "positive_numbers": {"a": "5", "b": "3", "expected": "8"},
        "negative_numbers": {"a": "-5", "b": "-3", "expected": "-8"},
        "mixed_signs": {"a": "-5", "b": "3", "expected": "-2"},
        "zero_sum": {"a": "5", "b": "-5", "expected": "0"},
        "decimals": {"a": "5.5", "b": "3.3", "expected": "8.8"},
        "large_numbers": {
            "a": "1e10",
            "b": "1e10",
            "expected": "20000000000"
        },
    }
    invalid_test_cases = {}  # Addition has no invalid cases


class TestSubtraction(BaseOperationTest):
    """Test Subtraction operation."""

    operation_class = Subtraction
    valid_test_cases = {
        "positive_numbers": {"a": "5", "b": "3", "expected": "2"},
        "negative_numbers": {"a": "-5", "b": "-3", "expected": "-2"},
        "mixed_signs": {"a": "-5", "b": "3", "expected": "-8"},
        "zero_result": {"a": "5", "b": "5", "expected": "0"},
        "decimals": {"a": "5.5", "b": "3.3", "expected": "2.2"},
        "large_numbers": {
            "a": "1e10",
            "b": "1e9",
            "expected": "9000000000"
        },
    }
    invalid_test_cases = {}  # Subtraction has no invalid cases


class TestMultiplication(BaseOperationTest):
    """Test Multiplication operation."""

    operation_class = Multiplication
    valid_test_cases = {
        "positive_numbers": {"a": "5", "b": "3", "expected": "15"},
        "negative_numbers": {"a": "-5", "b": "-3", "expected": "15"},
        "mixed_signs": {"a": "-5", "b": "3", "expected": "-15"},
        "multiply_by_zero": {"a": "5", "b": "0", "expected": "0"},
        "decimals": {"a": "5.5", "b": "3.3", "expected": "18.15"},
        "large_numbers": {
            "a": "1e5",
            "b": "1e5",
            "expected": "10000000000"
        },
    }
    invalid_test_cases = {}  # Multiplication has no invalid cases


class TestDivision(BaseOperationTest):
    """Test Division operation."""

    operation_class = Division
    valid_test_cases = {
        "positive_numbers": {"a": "6", "b": "2", "expected": "3"},
        "negative_numbers": {"a": "-6", "b": "-2", "expected": "3"},
        "mixed_signs": {"a": "-6", "b": "2", "expected": "-3"},
        "decimals": {"a": "5.5", "b": "2", "expected": "2.75"},
        "divide_zero": {"a": "0", "b": "5", "expected": "0"},
    }
    invalid_test_cases = {
        "divide_by_zero": {
            "a": "5",
            "b": "0",
            "error": ValidationError,
            "message": "Division by zero is not allowed"
        },
    }


class TestPower(BaseOperationTest):
    """Test Power operation."""

    operation_class = Power
    valid_test_cases = {
        "positive_base_and_exponent": {"a": "2", "b": "3", "expected": "8"},
        "zero_exponent": {"a": "5", "b": "0", "expected": "1"},
        "one_exponent": {"a": "5", "b": "1", "expected": "5"},
        "decimal_base": {"a": "2.5", "b": "2", "expected": "6.25"},
        "zero_base": {"a": "0", "b": "5", "expected": "0"},
    }
    invalid_test_cases = {
        "negative_exponent": {
            "a": "2",
            "b": "-3",
            "error": ValidationError,
            "message": "Negative exponents not supported"
        },
    }


class TestRoot(BaseOperationTest):
    """Test Root operation."""

    operation_class = Root
    valid_test_cases = {
        "square_root": {"a": "9", "b": "2", "expected": "3"},
        "cube_root": {"a": "27", "b": "3", "expected": "3"},
        "fourth_root": {"a": "16", "b": "4", "expected": "2"},
        "decimal_root": {"a": "2.25", "b": "2", "expected": "1.5"},
    }
    invalid_test_cases = {
        "negative_base": {
            "a": "-9",
            "b": "2",
            "error": ValidationError,
            "message": "Cannot calculate root of negative number"
        },
        "zero_root": {
            "a": "9",
            "b": "0",
            "error": ValidationError,
            "message": "Zero root is undefined"
        },
    }


class TestOperationFactory:
    """Test OperationFactory functionality."""

    def test_create_valid_operations(self):
        """Test creation of all valid operations."""
        operation_map = {
            'add': Addition,
            'subtract': Subtraction,
            'multiply': Multiplication,
            'divide': Division,
            'power': Power,
            'root': Root,
        }

        for op_name, op_class in operation_map.items():
            operation = OperationFactory.create_operation(op_name)
            assert isinstance(operation, op_class)
            # Test case-insensitive
            operation = OperationFactory.create_operation(op_name.upper())
            assert isinstance(operation, op_class)

    def test_create_invalid_operation(self):
        """Test creation of invalid operation raises error."""
        with pytest.raises(ValueError, match="Unknown operation: invalid_op"):
            OperationFactory.create_operation("invalid_op")

    def test_register_valid_operation(self):
        """Test registering a new valid operation."""
        class NewOperation(Operations):
            def execute(self, a: Decimal, b: Decimal) -> Decimal:
                return a

        OperationFactory.register_operation("new_op", NewOperation)
        operation = OperationFactory.create_operation("new_op")
        assert isinstance(operation, NewOperation)

    def test_register_invalid_operation(self):
        """Test registering an invalid operation class raises error."""
        class InvalidOperation:
            pass

        with pytest.raises(TypeError, match="Operation class must inherit"):
            OperationFactory.register_operation("invalid", InvalidOperation)

# number = Union[int, float]

# @pytest.mark.parametrize("a, b, expected", [
#     (1, 1, 2),            #adding positive integers
#     (0, 0, 0),            #adding zeros
#     (-10, 5, -5),         #adding negative and positive integers
#     (1.5, 2.5, 4.0),      #adding floats
#     (-10.5, 7.3, -3.2),   #adding negative and positive floats 
# ],
#     ids = [
#     "adding_positive_integers", 
#     "adding_zeros", 
#     "adding_negative_and_positive_integers",
#     "adding_positive_floats",
#     "adding_negative_and_positive_floats"
# ])

# def test_addition(a: number, b: number, expected: number) -> None:
#     result = Operations.addition(a, b)
#     assert result == expected, f"Expected addition({a}, {b} to equal {expected}, but got {result}."
#     ## assert addition(1,1) == 2

# @pytest.mark.parametrize("a, b, expected", [
#     (1, 1, 0),            #subtracting positive integers
#     (0, 0, 0),            #subtracting zeros
#     (-10, 5, -15),        #subtracting negative and positive integers
#     (1.5, 2.5, -1.0),     #subtracting floats
#     (-10.5, -7.3, -3.2),  #subtracting negative floats
# ],
#     ids = [
#     "subtracting_positive_integers", 
#     "subtracting_zeros", 
#     "subtracting_negative_and_positive_integers",
#     "subtracting_positive_floats",
#     "subtracting_negative_floats"
# ])

# def test_subtraction(a: number, b: number, expected: number) -> None:
#     result = Operations.subtraction(a, b)
#     assert result == expected, f"Expected subtraction({a}, {b}) to equal {expected}, but got {result}."
#     ## assert subtraction(1,1) == 0

# @pytest.mark.parametrize("a, b, expected", [
#     (1, 1, 1),            #multiplying positive integers
#     (0, 12, 0),           #multiplying zeros
#     (-10, 5, -50),        #multiplying negative and positive integers
#     (1.5, 2.5, 3.75),     #multiplying floats
#     (-10.5, 7.5, -78.75), #multiplying negative and positive floats 
#     (-12, -7, 84)         #multiplying negative integers
# ],
#     ids = [
#     "multiplying_positive_integers", 
#     "multiplying_zeros", 
#     "multiplying_negative_and_positive_integers",
#     "multiplying_positive_floats",
#     "multiplying_negative_and_positive_floats",
#     "multiplying_negative_integers"
# ])

# def test_multiplication(a: number, b: number, expected: number) -> None:
#     result = Operations.multiplication(a, b)
#     assert result == expected, f"Expected multiplication({a}, {b}) to equal {expected}, but got {result}."
#     ## assert multiplication(1,1) == 1

# @pytest.mark.parametrize("a, b, expected", [
#     (1, 1, 1),            #dividing positive integers   
#     (-12, -4, 3),         #dividing negative integers
#     (1.5, 0.5, 3.0),      #dividing floats
#     (-10.5, 7.0, -1.5),   #dividing negative and positive floats
#     (0, 12,0),            #dividing zero by a positive integer
# ],
#     ids = [
#     "dividing_positive_integers",
#     "dividing_negative_integers",
#     "dividing_floats",
#     "dividing_negative_and_positive_floats",
#     "dividing_zero_by_positive_integer"
#     ])

# def test_division_positive(a: number, b: number, expected: number) -> None:
#     result = Operations.division(a, b)
#     assert result == expected, f"Expected division({a}, {b}) to equal {expected}, but got {result}."
#    ## assert division(1,1) == 1

# ## def test_division_negative():
#    ## with pytest.raises(ZeroDivisionError):
#     ## division(1,0)

# @pytest.mark.parametrize("a, b", [
#     (2, 0),              #dividing by zero
#     (-2, 0),             #dividing negative by zero
#     (0, 0)               #dividing zero by zero 
# ],
#     ids = [
#     "dividing_positive_by_zero",
#     "dividing_negative_by_zero",
#     "dividing_zero_by_zero"
# ])

# def test_division_by_zero(a: number, b: number) -> None:
#     """Test division by zero."""
#     with pytest.raises(ValueError, match="Division by zero is not allowed.") as excinfo:
#         Operations.division(a, b)
#     assert "Division by zero is not allowed." in str(excinfo.value), f"Expected ValueError message 'Division by zero is not allowed.', but got {excinfo.value}."
#     ## division(1,0)

########################
# Calculation Model    #
########################

# from abc import ABC, abstractmethod
# from app.operations import Operations

from dataclasses import dataclass, field
import datetime
from decimal import Decimal, InvalidOperation
import logging
from typing import Any, Dict

from app.exceptions import OperationError


@dataclass
class Calculation:
    """
    Value Object representing a single calculation.

    This class encapsulates the details of a mathematical calculation, including the
    operation performed, operands involved, the result, and the timestamp of the
    calculation. It provides methods for performing the calculation, serializing
    the data for storage, and deserializing data to recreate a Calculation instance.
    """

    # Required fields
    operation: str          # The name of the operation (e.g., "Addition")
    operand1: Decimal       # The first operand in the calculation
    operand2: Decimal       # The second operand in the calculation

    # Fields with default values
    result: Decimal = field(init=False)  # The result of the calculation, computed post-initialization
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)  # Time when the calculation was performed

    def __post_init__(self):
        """
        Post-initialization processing.

        Automatically calculates the result of the operation after the Calculation
        instance is created.
        """
        self.result = self.calculate()

    def calculate(self) -> Decimal:
        """
        Execute calculation using the specified operation.

        Utilizes a dictionary to map operation names to their corresponding
        lambda functions, enabling dynamic execution of operations based on
        the operation name.

        Returns:
            Decimal: The result of the calculation.

        Raises:
            OperationError: If the operation is unknown or the calculation fails.
        """
        # Mapping of operation names to their corresponding functions
        operations = {
            "Addition": lambda x, y: x + y,
            "Subtraction": lambda x, y: x - y,
            "Multiplication": lambda x, y: x * y,
            "Division": lambda x, y: x / y if y != 0 else self._raise_div_zero(),
            "Power": lambda x, y: Decimal(pow(float(x), float(y))) if y >= 0 else self._raise_neg_power(),
            "Root": lambda x, y: (
                Decimal(pow(float(x), 1 / float(y))) 
                if x >= 0 and y != 0 
                else self._raise_invalid_root(x, y)
            )
        }

        # Retrieve the operation function based on the operation name
        op = operations.get(self.operation)
        if not op:
            raise OperationError(f"Unknown operation: {self.operation}")

        try:
            # Execute the operation with the provided operands
            return op(self.operand1, self.operand2)
        except (InvalidOperation, ValueError, ArithmeticError) as e:
            # Handle any errors that occur during calculation
            raise OperationError(f"Calculation failed: {str(e)}") #pragma: no cover

    @staticmethod
    def _raise_div_zero():  # pragma: no cover
        """
        Helper method to raise division by zero error.

        This method is called when a division by zero is attempted.
        """
        raise OperationError("Division by zero is not allowed")

    @staticmethod
    def _raise_neg_power():  # pragma: no cover
        """
        Helper method to raise negative power error.

        This method is called when a negative exponent is used in a power operation.
        """
        raise OperationError("Negative exponents are not supported")

    @staticmethod
    def _raise_invalid_root(x: Decimal, y: Decimal):  # pragma: no cover
        """
        Helper method to raise invalid root error.

        This method is called when an invalid root operation is attempted, such as
        taking the root of a negative number or using zero as the root degree.

        Args:
            x (Decimal): The number from which the root is taken.
            y (Decimal): The degree of the root.
        """
        if y == 0:
            raise OperationError("Zero root is undefined")
        if x < 0:
            raise OperationError("Cannot calculate root of negative number")
        raise OperationError("Invalid root operation")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert calculation to dictionary for serialization.

        This method transforms the Calculation instance into a dictionary format,
        facilitating easy storage and retrieval (e.g., saving to a file).

        Returns:
            Dict[str, Any]: A dictionary containing the calculation data in a serializable format.
        """
        return {
            'operation': self.operation,
            'operand1': str(self.operand1),
            'operand2': str(self.operand2),
            'result': str(self.result),
            'timestamp': self.timestamp.isoformat()
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Calculation':
        """
        Create calculation from dictionary.

        This method reconstructs a Calculation instance from a dictionary, ensuring
        that all required fields are present and correctly formatted.

        Args:
            data (Dict[str, Any]): Dictionary containing calculation data.

        Returns:
            Calculation: A new instance of Calculation with data populated from the dictionary.

        Raises:
            OperationError: If data is invalid or missing required fields.
        """
        try:
            # Create the calculation object with the original operands
            calc = Calculation(
                operation=data['operation'],
                operand1=Decimal(data['operand1']),
                operand2=Decimal(data['operand2'])
            )

            # Set the timestamp from the saved data
            calc.timestamp = datetime.datetime.fromisoformat(data['timestamp'])

            # Verify the result matches (helps catch data corruption)
            saved_result = Decimal(data['result'])
            if calc.result != saved_result:
                logging.warning(
                    f"Loaded calculation result {saved_result} "
                    f"differs from computed result {calc.result}"
                )  # pragma: no cover

            return calc

        except (KeyError, InvalidOperation, ValueError) as e:
            raise OperationError(f"Invalid calculation data: {str(e)}")

    def __str__(self) -> str:
        """
        Return string representation of calculation.

        Provides a human-readable representation of the calculation, showing the
        operation performed and its result.

        Returns:
            str: Formatted string showing the calculation and result.
        """
        return f"{self.operation}({self.operand1}, {self.operand2}) = {self.result}"

    def __repr__(self) -> str:
        """
        Return detailed string representation of calculation.

        Provides a detailed and unambiguous string representation of the Calculation
        instance, useful for debugging.

        Returns:
            str: Detailed string showing all calculation attributes.
        """
        return (
            f"Calculation(operation='{self.operation}', "
            f"operand1={self.operand1}, "
            f"operand2={self.operand2}, "
            f"result={self.result}, "
            f"timestamp='{self.timestamp.isoformat()}')"
        )

    def __eq__(self, other: object) -> bool:
        """
        Check if two calculations are equal.

        Compares two Calculation instances to determine if they represent the same
        operation with identical operands and results.

        Args:
            other (object): Another calculation to compare with.

        Returns:
            bool: True if calculations are equal, False otherwise.
        """
        if not isinstance(other, Calculation):
            return NotImplemented
        return (
            self.operation == other.operation and
            self.operand1 == other.operand1 and
            self.operand2 == other.operand2 and
            self.result == other.result
        )

    def format_result(self, precision: int = 10) -> str:
        """
        Format the calculation result with specified precision.

        This method formats the result to a fixed number of decimal places,
        removing any trailing zeros for a cleaner presentation.

        Args:
            precision (int, optional): Number of decimal places to show. Defaults to 10.

        Returns:
            str: Formatted string representation of the result.
        """
        try:
            # Remove trailing zeros and format to specified precision
            return str(self.result.normalize().quantize(
                Decimal('0.' + '0' * precision)
            ).normalize())
        except InvalidOperation:  # pragma: no cover
            return str(self.result)

#class Calculation(ABC):
#   """
#    The Calculation class is an Abstract Base Class (ABC) that defines a blueprint 
#    for all mathematical calculations in the calculator program. This class establishes 
#    a consistent interface that all calculation types (such as addition, subtraction, etc.) 
#   must follow. 
    
#    Why Use an Abstract Base Class?
#    - **Abstraction**: By using an ABC, we focus on "what" calculations need to do (execute an operation) 
#      rather than "how" each specific operation is implemented. This simplifies our design.
#    - **Polymorphism**: By providing a standard interface, any Calculation subclass can be used 
#      interchangeably, allowing the program to treat each type of calculation in a consistent manner.
#    - **Enforcing Consistency**: The abstract `execute` method enforces that all subclasses implement 
#      their own specific version of the calculation logic, making sure that each type of calculation 
#      has an `execute` method.
#      rather than "how" each specific operation is implemented. This simplifies our design.
#    - **Polymorphism**: By providing a standard interface, any Calculation subclass can be used 
#      interchangeably, allowing the program to treat each type of calculation in a consistent manner.
#    - **Enforcing Consistency**: The abstract `execute` method enforces that all subclasses implement 
#      their own specific version of the calculation logic, making sure that each type of calculation 
#      has an `execute` method.
#    """

#    def __init__(self, a: float, b: float) -> None:
#        """
#        Initializes a Calculation instance with two operands (numbers involved in the calculation).
        
#       **Why Have an Initializer?**
#        - This initializer method ensures that each Calculation object will have two numbers (`a` and `b`) 
#          to work with, no matter the specific type of calculation.
#        - Encapsulating the operands within an instance allows each Calculation object to maintain its own 
#          state (values of `a` and `b`), supporting **Object-Oriented Design** principles.

#        **Parameters:**
#        - `a (float)`: The first operand.
#        - `b (float)`: The second operand.
#        """
#        self.a: float = a  # Stores the first operand as a floating-point number.
#        self.b: float = b  # Stores the second operand as a floating-point number.

#    @abstractmethod
#   def execute(self) -> float:
##        """
##        Abstract method to perform the calculation. Subclasses will provide specific 
##        implementations of this method, defining the arithmetic for each operation.

##        **Why Use an Abstract Method?**
##        - Enforces that each subclass provides its own specific version of `execute`, 
##          which is crucial for following the interface defined by Calculation.
##        - Abstract methods define "must-have" methods for subclasses. By including `execute` here, 
##          we ensure that any class inheriting from Calculation will have this method, making 
##          it easier to work with multiple types of calculations in a flexible way.
        
#        **Returns:**
#        - `float`: The result of the calculation.
#        """
#        pass  # The actual implementation will be provided by the subclass. # pragma: no cover

#    def __str__(self) -> str:
##        """
##        Provides a user-friendly string representation of the Calculation instance, 
##        showing the operation name, operands, and result. This enhances **Readability** 
##        and **Debugging** by giving a clear output for each calculation.

##        **Returns:**
##        - `str`: A string describing the calculation and its result.
##        """
##        result = self.execute()  # Run the calculation to get the result.
##        operation_name = self.__class__.__name__.replace('Calculation', '')  # Derive operation name.
##        return f"{self.__class__.__name__}: {self.a} {operation_name} {self.b} = {result}"

#    def __repr__(self) -> str:
##        """
##        Provides a technical, unambiguous representation of the Calculation instance 
##        showing the class name and operand values. This is useful for debugging 
##        since it gives a clear and consistent format for all Calculation objects.

##        **Returns:**
##        - `str`: A string containing the class name and operands.
##        """
##        return f"{self.__class__.__name__}(a={self.a}, b={self.b})"

# -----------------------------------------------------------------------------------
# Factory Class: CalculationFactory
# -----------------------------------------------------------------------------------
# class CalculationFactory:
#    """
#    The CalculationFactory is a **Factory Class** responsible for creating instances 
#    of Calculation subclasses. This design pattern allows us to encapsulate the 
#    logic of object creation and make it flexible.#

#    **Why Use a Factory Class?**
#    - **Single Responsibility Principle (SRP)**: The factory only deals with object creation. 
#      This keeps our code organized, as the logic for creating different calculations is 
#      separated from the calculations themselves.
#    - **Open/Closed Principle (OCP)**: We can add new calculation types without changing 
#      the existing codebase. We simply register new calculation classes, making our 
# #      code extensible and flexible to future modifications.
#   """

#    # _calculations is a dictionary that holds a mapping of calculation types 
#     (like "add" or "subtract") to their respective classes.
#   def register_calculation(cls, calculation_type: str):
#        """
#        This method is a decorator used to register a specific Calculation subclass 
#        under a unique calculation type. Registering classes with string identifiers 
# #        like "add" or "multiply" enables easy access to different operations 
# #        dynamically at runtime.

#        **Parameters:**
# #        - `calculation_type (str)`: A short identifier for the type of calculation 
# #          (e.g., 'add' for addition).
        
# #        **Benefits of Using a Decorator for Registration:**
# #        - **Modularity**: By using a decorator, we can easily add new calculations by 
# #          annotating new subclasses with `@CalculationFactory.register_calculation`.
# #        - **Dynamic Binding**: This approach binds each calculation type to a class dynamically, 
# #          allowing us to extend our application without altering the core logic.
# #        """
#        def decorator(subclass):
#            # Convert calculation_type to lowercase to ensure consistency.
#            calculation_type_lower = calculation_type.lower()
# #            # Check if the calculation type has already been registered to avoid duplication.
# #            if calculation_type_lower in cls._calculations:
# #                raise ValueError(f"Calculation type '{calculation_type}' is already registered.")
# #            # Register the subclass in the _calculations dictionary.
# #            cls._calculations[calculation_type_lower] = subclass
# #            return subclass  # Return the subclass for chaining or additional use.
# #        return decorator  # Return the decorator function.

#    @classmethod
#    def create_calculation(cls, calculation_type: str, a: float, b: float) -> Calculation:
# #        """
# #        Factory method that creates instances of Calculation subclasses based on 
# #        a specified calculation type.

# #        **Parameters:**
# #        - `calculation_type (str)`: The type of calculation ('add', 'subtract', 'multiply', 'divide').
# #        - `a (float)`: The first operand.
# #        - `b (float)`: The second operand.
# #        
# #        **Returns:**
# #        - `Calculation`: An instance of the appropriate Calculation subclass.

# #        **How Does This Help?**
# #        - By centralizing object creation here, we only need to specify calculation types 
# #          as strings, making it easy to choose different calculations dynamically. 
# #        - **Error Handling**: If the specified type is not available, we provide a 
# #          clear error message listing valid options, helping prevent errors and 
# #          ensuring the user knows the supported types.
# #        """
#        calculation_type_lower = calculation_type.lower()
#        calculation_class = cls._calculations.get(calculation_type_lower)
#        # If the type is unsupported, raise an error with the available types.
# #        if not calculation_class:
    #        available_types = ', '.join(cls._calculations.keys())
    #        raise ValueError(f"Unsupported calculation type: '{calculation_type}'. Available types: {available_types}")
    #    # Create and return an instance of the requested calculation class with the provided operands.
    #     return calculation_class(a, b)

# -----------------------------------------------------------------------------------
# Concrete Calculation Classes
# -----------------------------------------------------------------------------------

# Each of these classes defines a specific calculation type (addition, subtraction, 
# multiplication, or division). These classes inherit from Calculation, implementing 
# the `execute` method to perform the specific arithmetic operation. 

#@CalculationFactory.register_calculation('add')
#class AddCalculation(Calculation):
#    """
#    AddCalculation represents an addition operation between two numbers.
    
#    **Why Create Separate Classes for Each Operation?**
#    - **Polymorphism**: Each calculation type can be used interchangeably through the `execute` method.
#    - **Modularity**: Encapsulating each operation in a separate class makes it easy to 
#      modify, test, or extend without affecting other calculations.
#    - **Clear Responsibility**: Each class has a clear, single purpose, making the code easier to read.
#    """

#    def execute(self) -> float:
#        # Calls the addition method from the Operation module to perform the addition.
#        return Operations.addition(self.a, self.b)


#@CalculationFactory.register_calculation('subtract')
#class SubtractCalculation(Calculation):
#    """
#    SubtractCalculation represents a subtraction operation between two numbers.
#    
#    **Implementation Note**: This class specifically handles subtraction, keeping 
#    the implementation separate from other operations.
#    """

#    def execute(self) -> float:
        # Calls the subtraction method from the Operation module to perform the subtraction.
#        return Operations.subtraction(self.a, self.b)


#@CalculationFactory.register_calculation('multiply')
#class MultiplyCalculation(Calculation):
#    """
#    MultiplyCalculation represents a multiplication operation.
    
#    By encapsulating the multiplication logic here, we achieve a clear separation of 
#    concerns, making it easy to adjust the multiplication logic without affecting other calculations.
#    """

#    def execute(self) -> float:
#        # Calls the multiplication method from the Operation module to perform the multiplication.
#        return Operations.multiplication(self.a, self.b)

#@CalculationFactory.register_calculation('divide')
#class DivideCalculation(Calculation):
##    """
##    """
#    DivideCalculation represents a division operation.
    
#    **Special Case - Division by Zero**: Division requires extra error handling to 
#    prevent dividing by zero, which would cause an error in the program. This class 
#    checks if the second operand is zero before performing the operation.
##    """

#    def execute(self) -> float:
##        # Before performing division, check if `b` is zero to avoid ZeroDivisionError.
##        if self.b == 0:
##            raise ZeroDivisionError("Cannot divide by zero.")
##        # Calls the division method from the Operation module to perform the division.
##        return Operations.division(self.a, self.b)

# @CalculationFactory.register_calculation('power')
# class PowerCalculation(Calculation):
#     """
#     MultiplyCalculation represents a multiplication operation.
    
#     By encapsulating the multiplication logic here, we achieve a clear separation of 
#     concerns, making it easy to adjust the multiplication logic without affecting other calculations.
#     """

#     def execute(self) -> float:
#         # Calls the multiplication method from the Operation module to perform the multiplication.
#         return Operation.power(self.a, self.b) # pragma: no cover
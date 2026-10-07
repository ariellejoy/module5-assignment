########################
# Calculator Class      #
########################

import traceback
import sys
#import readline #this will enable history and editing
#from typing import List

from decimal import Decimal
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

#from app.calculation import Calculation, CalculationFactory
from app.calculation import Calculation

from app.calculator_config import CalculatorConfig
from app.calculator_memento import CalculatorMemento
from app.exceptions import OperationError, ValidationError
from app.history import HistoryObserver
from app.input_validators import InputValidator

#from app.operations import Operations
from app.operations import Operations

# Type aliases for better readability
Number = Union[int, float, Decimal]
CalculationResult = Union[Number, str]


class Calculator:
    """
    Main calculator class implementing multiple design patterns.

    This class serves as the core of the calculator application, managing operations,
    calculation history, observers, configuration settings, and data persistence.
    It integrates various design patterns to enhance flexibility, maintainability, and
    scalability.
    """

    def __init__(self, config: Optional[CalculatorConfig] = None):
        """
        Initialize calculator with configuration.

        Args:
            config (Optional[CalculatorConfig], optional): Configuration settings for the calculator.
                If not provided, default settings are loaded based on environment variables.
        """
        if config is None:
            # Determine the project root directory if no configuration is provided
            current_file = Path(__file__)
            project_root = current_file.parent.parent
            config = CalculatorConfig(base_dir=project_root)

        # Assign the configuration and validate its parameters
        self.config = config
        self.config.validate()

        # Ensure that the log directory exists
        os.makedirs(self.config.log_dir, exist_ok=True)

        # Set up the logging system
        self._setup_logging()

        # Initialize calculation history and operation strategy
        self.history: List[Calculation] = []
        self.operation_strategy: Optional[Operation] = None

        # Initialize observer list for the Observer pattern
        self.observers: List[HistoryObserver] = []

        # Initialize stacks for undo and redo functionality using the Memento pattern
        self.undo_stack: List[CalculatorMemento] = []
        self.redo_stack: List[CalculatorMemento] = []

        # Create required directories for history management
        self._setup_directories()

        try:
            # Attempt to load existing calculation history from file
            self.load_history()
        except Exception as e: #pragma: no cover
            # Log a warning if history could not be loaded
            logging.warning(f"Could not load existing history: {e}") 

        # Log the successful initialization of the calculator
        logging.info("Calculator initialized with configuration")

    def _setup_logging(self) -> None:
        """
        Configure the logging system.

        Sets up logging to a file with a specified format and log level.
        """
        try:
            # Ensure the log directory exists
            os.makedirs(self.config.log_dir, exist_ok=True)
            log_file = self.config.log_file.resolve()

            # Configure the basic logging settings
            logging.basicConfig(
                filename=str(log_file),
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                force=True  # Overwrite any existing logging configuration
            )
            logging.info(f"Logging initialized at: {log_file}")
        except Exception as e:
            # Print an error message and re-raise the exception if logging setup fails
            print(f"Error setting up logging: {e}")
            raise

    def _setup_directories(self) -> None:
        """
        Create required directories.

        Ensures that all necessary directories for history management exist.
        """
        self.config.history_dir.mkdir(parents=True, exist_ok=True)

    def add_observer(self, observer: HistoryObserver) -> None:
        """
        Register a new observer.

        Adds an observer to the list, allowing it to receive updates when new
        calculations are performed.

        Args:
            observer (HistoryObserver): The observer to be added.
        """
        self.observers.append(observer)
        logging.info(f"Added observer: {observer.__class__.__name__}")

    def remove_observer(self, observer: HistoryObserver) -> None:
        """
        Remove an existing observer.

        Removes an observer from the list, preventing it from receiving further updates.

        Args:
            observer (HistoryObserver): The observer to be removed.
        """
        self.observers.remove(observer)
        logging.info(f"Removed observer: {observer.__class__.__name__}")

    def notify_observers(self, calculation: Calculation) -> None:
        """
        Notify all observers of a new calculation.

        Iterates through the list of observers and calls their update method,
        passing the new calculation as an argument.

        Args:
            calculation (Calculation): The latest calculation performed.
        """
        for observer in self.observers:
            observer.update(calculation)

    def set_operation(self, operation: Operations) -> None:
        """
        Set the current operation strategy.

        Assigns the operation strategy that will be used for performing calculations.
        This is part of the Strategy pattern, allowing the calculator to switch between
        different operation algorithms dynamically.

        Args:
            operation (Operation): The operation strategy to be set.
        """
        self.operation_strategy = operation
        logging.info(f"Set operation: {operation}")

    def perform_operation(
        self,
        a: Union[str, Number],
        b: Union[str, Number]
    ) -> CalculationResult:
        """
        Perform calculation with the current operation.

        Validates and sanitizes user inputs, executes the calculation using the
        current operation strategy, updates the history, and notifies observers.

        Args:
            a (Union[str, Number]): The first operand, can be a string or a numeric type.
            b (Union[str, Number]): The second operand, can be a string or a numeric type.

        Returns:
            CalculationResult: The result of the calculation.

        Raises:
            OperationError: If no operation is set or if the operation fails.
            ValidationError: If input validation fails.
        """
        if not self.operation_strategy:
            raise OperationError("No operation set") #pragma: no cover

        try:
            # Validate and convert inputs to Decimal
            validated_a = InputValidator.validate_number(a, self.config)
            validated_b = InputValidator.validate_number(b, self.config)

            # Execute the operation strategy
            result = self.operation_strategy.execute(validated_a, validated_b)

            # Create a new Calculation instance with the operation details
            calculation = Calculation(
                operation=str(self.operation_strategy),
                operand1=validated_a,
                operand2=validated_b
            )

            # Save the current state to the undo stack before making changes
            self.undo_stack.append(CalculatorMemento(self.history.copy()))

            # Clear the redo stack since new operation invalidates the redo history
            self.redo_stack.clear()

            # Append the new calculation to the history
            self.history.append(calculation)

            # Ensure the history does not exceed the maximum size
            if len(self.history) > self.config.max_history_size:
                self.history.pop(0)

            # Notify all observers about the new calculation
            self.notify_observers(calculation)

            return result

        except ValidationError as e:
            # Log and re-raise validation errors
            logging.error(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            # Log and raise operation errors for any other exceptions
            logging.error(f"Operation failed: {str(e)}")
            raise OperationError(f"Operation failed: {str(e)}") #pragma: no cover

    def save_history(self) -> None:
        """
        Save calculation history to a CSV file using pandas.

        Serializes the history of calculations and writes them to a CSV file for
        persistent storage. Utilizes pandas DataFrames for efficient data handling.

        Raises:
            OperationError: If saving the history fails.
        """
        try:
            # Ensure the history directory exists
            self.config.history_dir.mkdir(parents=True, exist_ok=True)

            history_data = []
            for calc in self.history:
                # Serialize each Calculation instance to a dictionary
                history_data.append({
                    'operation': str(calc.operation),
                    'operand1': str(calc.operand1),
                    'operand2': str(calc.operand2),
                    'result': str(calc.result),
                    'timestamp': calc.timestamp.isoformat()
                })

            if history_data:
                # Create a pandas DataFrame from the history data
                df = pd.DataFrame(history_data)
                # Write the DataFrame to a CSV file without the index
                df.to_csv(self.config.history_file, index=False)
                logging.info(f"History saved successfully to {self.config.history_file}")
            else:
                # If history is empty, create an empty CSV with headers
                pd.DataFrame(columns=['operation', 'operand1', 'operand2', 'result', 'timestamp']
                           ).to_csv(self.config.history_file, index=False)
                logging.info("Empty history saved")

        except Exception as e:
            # Log and raise an OperationError if saving fails
            logging.error(f"Failed to save history: {e}")
            raise OperationError(f"Failed to save history: {e}") #pragma: no cover

    def load_history(self) -> None:
        """
        Load calculation history from a CSV file using pandas.

        Reads the calculation history from a CSV file and reconstructs the
        Calculation instances, restoring the calculator's history.

        Raises:
            OperationError: If loading the history fails.
        """
        try:
            if self.config.history_file.exists():
                # Read the CSV file into a pandas DataFrame
                df = pd.read_csv(self.config.history_file)
                if not df.empty:
                    # Deserialize each row into a Calculation instance
                    self.history = [
                        Calculation.from_dict({
                            'operation': row['operation'],
                            'operand1': row['operand1'],
                            'operand2': row['operand2'],
                            'result': row['result'],
                            'timestamp': row['timestamp']
                        })
                        for _, row in df.iterrows()
                    ]
                    logging.info(f"Loaded {len(self.history)} calculations from history")
                else:
                    logging.info("Loaded empty history file")
            else:
                # If no history file exists, start with an empty history
                logging.info("No history file found - starting with empty history")
        except Exception as e:
            # Log and raise an OperationError if loading fails
            logging.error(f"Failed to load history: {e}")
            raise OperationError(f"Failed to load history: {e}") #pragma: no cover

    def get_history_dataframe(self) -> pd.DataFrame:
        """
        Get calculation history as a pandas DataFrame.

        Converts the list of Calculation instances into a pandas DataFrame for
        advanced data manipulation or analysis.

        Returns:
            pd.DataFrame: DataFrame containing the calculation history.
        """
        history_data = []
        for calc in self.history:
            history_data.append({
                'operation': str(calc.operation),
                'operand1': str(calc.operand1),
                'operand2': str(calc.operand2),
                'result': str(calc.result),
                'timestamp': calc.timestamp
            })
        return pd.DataFrame(history_data)

    def show_history(self) -> List[str]:
        """
        Get formatted history of calculations.

        Returns a list of human-readable strings representing each calculation.

        Returns:
            List[str]: List of formatted calculation history entries.
        """
        return [
            f"{calc.operation}({calc.operand1}, {calc.operand2}) = {calc.result}"
            for calc in self.history
        ]

    def clear_history(self) -> None:
        """
        Clear calculation history.

        Empties the calculation history and clears the undo and redo stacks.
        """
        self.history.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        logging.info("History cleared")

    def undo(self) -> bool:
        """
        Undo the last operation.

        Restores the calculator's history to the state before the last calculation
        was performed.

        Returns:
            bool: True if an operation was undone, False if there was nothing to undo.
        """
        if not self.undo_stack:
            return False
        # Pop the last state from the undo stack
        memento = self.undo_stack.pop()
        # Push the current state onto the redo stack
        self.redo_stack.append(CalculatorMemento(self.history.copy()))
        # Restore the history from the memento
        self.history = memento.history.copy()
        return True

    def redo(self) -> bool:
        """
        Redo the previously undone operation.

        Restores the calculator's history to the state before the last undo.

        Returns:
            bool: True if an operation was redone, False if there was nothing to redo.
        """
        if not self.redo_stack:
            return False
        # Pop the last state from the redo stack
        memento = self.redo_stack.pop()
        # Push the current state onto the undo stack
        self.undo_stack.append(CalculatorMemento(self.history.copy()))
        # Restore the history from the memento
        self.history = memento.history.copy()
        return True

#creating a function that will display a help message / instructions 
def display_help() -> None:
    """Display help message with instructions."""

    help_message = """
    REPL Calculator Help
    --------------------
    In order to use the REPL calculator: input <operation> <num1> <num2> to perform a specific operation with 2 numbers 
    
    Supported operations include: 
    - add
    - subtract (note: this subtracts the second number from the first)
    - multiply
    - divide (note: this divides the first number by the second)

    Some special commands that could be helpful: 
    - help : Displays this help message
    - history : Shows your history of calculations 
    - exit : Exits the calculator 

    Example operations: 
    add 1 1 
    subtract 5 3
    multiply 2 4
    divide 10 2
    """
    print(help_message)

#creating a function that will display calcultions history 
def display_history (history: List[Calculation]) -> None: 
    """Display history of calculations preformed during the session (read: python3 main.py is running and REPL app is open)"""

    if not history: 
        print("No calculations have been performed yet.")
    else: 
        print ("Calculation History:")
        for idx, calculation in enumerate(history, start=1):
            print(f"{idx}. {calculation}")

# Now we're going to create the main function called "calculator". 
# A function is just a block of code that does something when you call it, kind of like a recipe that tells the 
# computer what to do.
def calculator():
    """REPL calculator that performs addition, subtraction, multiplication, and division. This calculator now uses Calculation classes"""
    
    #initializing list to keep track of history
    history: List[Calculation] = []

    # First, we print a message to welcome the user to the calculator.
    print("Welcome to the calculator REPL! Type 'help' for more instructions or 'exit' to quit")
    
    # This is the part where the calculator keeps running. The 'while True' means we are going to keep 
    # doing something (in this case, asking the user for input) until we tell it to stop.
    while True:
        # Now we ask the user to type something, like "add 5 3". 
        # This will get the operation (like "add") and two numbers from the user.
        #user_input = input("Enter an operation (add, subtract, multiply, divide) and two numbers, or 'exit' to quit: ")
        try: 
            user_input: str = input(">> ").strip()
            if not user_input:
                continue # pragma no cover

            command = user_input.lower() #this will handle special commands

            if command == "help":
                display_help()
                continue #pragma: no cover
            elif command == "history":
                display_history(history)
                continue #pragma: no cover
            # This part checks if the user typed "exit". If they did, we print a message and stop the calculator.
            #if user_input.lower() == "exit":
            elif command == "exit":
                print("Exiting calculator now... Thank you!")
                sys.exit(0)

            try: 
                operation_map = {
                    "add": "Addition",
                    "subtract": "Subtraction",
                    "multiply": "Multiplication",
                    "divide": "Division",
                    "power": "Power",
                    "root": "Root",}

                operation, num1_str, num2_str = user_input.split()

            # Now we split the input into three parts: the operation (add, subtract, etc.) and the two numbers.
                operation = operation_map.get(operation.lower())
            # We have to make sure the numbers are actually numbers, so we convert them to floats.
            #num1, num2 = float(num1), float(num2)
                num1 = Decimal(num1_str)
                num2 = Decimal(num2_str)
            except ValueError: #pragma: no cover
            # If the user doesn't type something correctly, like typing letters where numbers should be, we show an error.
                print("Invalid input. Please follow the format: <operation> <num1> <num2>")
                print("Type 'help' for more instructions!")
                continue  # This "continue" means: try again by going back to the top of the loop.

            try: 
                calculation = Calculation(operation, num1, num2)
            except ValueError as ve: #pragma: no cover
                print(ve)
                print("Type 'help' for more instructions and the list of supported operations!")
                continue  # This "continue" means: try again by going back to the top of the loop.

            # Now we check what operation the user asked for and call the right function (addition, subtraction, etc.).
            try: 
                calculation = Calculation(operation, num1, num2)
                result = calculation.result
            except ZeroDivisionError: #pragma: no cover
                print("Error: Division by zero is not allowed.")
                print("Please try again!")
                continue  # This "continue" means: try again by going back to the top of the loop.  
            #except Exception as e:
            except Exception as e: #pragma: no cover
                print(f"An error has occurred during calculation: {e}")
                print("Please try again!")
                continue  # This "continue" means: try again by going back to the top of the loop.

             # Finally, we print the result of the operation (for example, "Result: 8").
            result_str: str = f"{calculation}"
            print(f"Result: {result_str}")
            history.append(calculation)
        
        except KeyboardInterrupt: #pragma: no cover
            # EAFP example for handling unexpected interruption
            # Instead of checking if the user pressed Ctrl+C before each input,
            # we handle the KeyboardInterrupt exception.
            print("\nKeyboard interrupt detected. Exiting calculator. Goodbye!")
            sys.exit(0)

        except EOFError: #pragma: no cover
            # EAFP example for handling EOF (Ctrl+D)
            # Similar to KeyboardInterrupt, we handle the EOFError exception.
            print("\nEOF detected. Exiting calculator. Goodbye!")
            sys.exit(0)

if __name__ == "__main__":
    calculator() # pragma no cover

        #if operation == "add":
            #result = Operations.addition(num1, num2)  # We call the addition function to add the two numbers.
        #elif operation == "subtract":
            #result = Operations.subtraction(num1, num2)  # We call the subtraction function to subtract the two numbers.
        #elif operation == "multiply":
            #result = Operations.multiplication(num1, num2)  # We call the multiplication function to multiply the two numbers.
        #elif operation == "divide":
            #try:
               # result = Operations.division(num1, num2)  # We call the division function to divide the two numbers.
           # except ValueError as e:
                # This part handles the case where someone tries to divide by zero, which we can't do.
                # The division function will throw an error if someone tries dividing by zero, and we catch that error here.
                #print(e)  # Show the error message.
                #continue  # Go back to the top of the loop and try again.
        #else:
            # If the user types an operation we don't understand, we show them a message.
            #print(f"Unknown operation '{operation}'. Supported operations: add, subtract, multiply, divide.")
            #continue  # Go back to the top of the loop and try again.
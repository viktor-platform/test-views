## IMPORTS MODULES
from msvcrt import kbhit
import unittest
import inspect
try:
    from hypothesis import given, strategies as st, settings
    import viktor as vkt
    from munch import munchify
except ModuleNotFoundError:
    raise ModuleNotFoundError("Please add 'hypothesis' and 'viktor' to your requirements.txt and run 'viktor-cli install'")

try:
    from app import Controller, Parametrization
except:
    raise ModuleNotFoundError("There was no app.py file found in the directory")

### ------------------------------------------------------------
### Hypothesis strategy
### ------------------------------------------------------------

@st.composite
def params_strategy(draw, parametrization : vkt.ViktorParametrization):
    # Parse the Parametrization to retrieve values
    dict_fields = extract_fields(parametrization=parametrization)

    # Per parameter, create a Hypothesis strategy
    rules = generate_individual_strategies(dict_fields)

    # Build nested structure
    nested_rules = build_nested_strategy(rules)
    
    # Convert to Hypothesis strategy
    strategy = nested_dict_to_strategy(nested_rules)

    return munchify(draw(strategy))


class TestViewBehavior(unittest.TestCase):
    """
    Test that all views handle inputs gracefully.
    
    This test class automatically tests your Viktor application by:
    1. Generating random input data for all your parametrization fields
    2. Calling each view method with this random data
    3. Verifying that the methods don't crash and return valid results (or raise a vkt.UserError)
    
    This helps ensure your application is robust and can handle any user input.
    """
    
    def setUp(self):
        """Set up test controller."""
        self.controller = Controller()
        self.all_methods = [f for f, _ in inspect.getmembers(Controller, predicate=inspect.ismethod)]
        

    @given(params_strategy(Parametrization))
    @settings(deadline=2000000, max_examples=100)
    def test_view_handles_input_gracefully(self, params):
        """
        Test that any view method handles inputs gracefully.
        
        This test automatically uses a custom Hypothesis strategy to generate params, 
        and will pass if the result is a View or raises a vkt.UserError. 
        """
        for view_method in self.all_methods:
            try:
                # Get the view method from the controller
                method = getattr(self.controller, view_method)
                
                # Call the view method with the generated parameters
                result = method(self.controller, params=params)
                
                # Check that the method returned a valid Viktor view result
                if not isinstance(result, vkt.views._ViewResult):
                    self.fail(
                        f"View method '{view_method}' failed!\n\n"
                    )
            except vkt.UserError:
                # UserError is expected, so we pass
                pass


### ------------------------------------------------------------
### Helper functions
### ------------------------------------------------------------


def extract_fields(parametrization, dict_fields = {}, current_path=''):
    """
    Recursively gets the fields from a Parametrization object and builds nested structure.
    """
    fields = [f for f in dir(parametrization) if not f.startswith('_')]
    if len(fields) == 0:
        fields = [f for f in parametrization._attrs if not f.startswith('_')]
    
    for field in fields:
        field_obj = getattr(parametrization, field)
        
        if isinstance(field_obj, vkt.parametrization.Field):
            # For regular fields, store with full path
            full_path = f'{current_path}.{field}' if current_path else field
            dict_fields[full_path] = field_obj
        elif isinstance(field_obj, (vkt.Table, vkt.DynamicArray)):
            # For Table objects, store with full path
            full_path = f'{current_path}.{field}' if current_path else field
            dict_fields[full_path] = field_obj
        elif isinstance(field_obj, (
            vkt.parametrization.Section,
            vkt.parametrization.Page,
            vkt.parametrization.Step,
            vkt.parametrization.Tab
            )):
            # For nested objects (like Sections), recurse
            dict_fields = extract_fields(field_obj, dict_fields, f'{current_path}.{field}' if current_path else field)
        else:
            pass
        
    return dict_fields


def generate_individual_strategies(dict_fields):
    """Generate individual strategies for each field"""
    strategies = {}
    for path, field_obj in dict_fields.items():
        strategy = _handle_field(field_obj)
        if strategy is not None:
            strategies[path] = strategy
    return strategies


def build_nested_strategy(strategies):
    """Convert flattened strategies to nested dictionary structure"""
    nested_strategies = {}
    
    for path, strategy in strategies.items():
        # Split the path into parts
        parts = path.split('.')
        
        # Navigate/create nested structure
        current = nested_strategies
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the final strategy
        current[parts[-1]] = strategy
    
    return nested_strategies


def nested_dict_to_strategy(nested_dict):
    """Convert nested dictionary structure to Hypothesis strategy"""
    if isinstance(nested_dict, dict):
        # If it's a dictionary, create a fixed_dictionaries strategy
        strategy_dict = {}
        for key, value in nested_dict.items():
            strategy_dict[key] = nested_dict_to_strategy(value)
        return st.fixed_dictionaries(strategy_dict)
    else:
        # If it's not a dictionary, it should be a strategy already
        return nested_dict



def _handle_field(_field_obj):
    # TODO: DateField / ColorField / Entity?Fields / GeoPoints / Stuff
    if isinstance(_field_obj, vkt.NumberField):
        return st.floats(_field_obj._min, _field_obj._max)
    elif isinstance(_field_obj, vkt.BooleanField):
        return st.booleans()
    elif isinstance(_field_obj, (vkt.OptionField, vkt.AutocompleteField, vkt.MultiSelectField)):
        options = [o.label for o in _field_obj._options]
        # TODO: Find a way to create params to also call the dynamic options function
        # options = field_obj._options if not field_obj._dynamic_options else field_obj._dynamic_options(params)
        if len(options) > 0:
            return st.sampled_from(options)
        else:
            return None
    elif isinstance(_field_obj, (vkt.TextField)):
        return st.text()
    elif isinstance(_field_obj, (vkt.Table, vkt.DynamicArray)):
        return _handle_table(_field_obj)
    elif isinstance(_field_obj, (vkt.FileField)):
        raise ValueError("FileField is not supported yet")
    else:
        print(f"File type of '{type(_field_obj)}' is not supported yet. Skipping...")
        return None


def _handle_table(table_obj):
    """
    Handle vkt.Table objects by creating strategies for each column.
    Returns a strategy that generates lists of dictionaries.
    """
    # Get the column fields from the table
    array_fields = [n for n in list(table_obj._attrs.keys()) if not n.startswith("_")]
    
    # Create strategies for each column
    column_strategies = {}
    for field_name in array_fields:
        field_strategy = _handle_field(getattr(table_obj, field_name))
        if field_strategy is not None:
            column_strategies[field_name] = field_strategy
    
    # Create a strategy for a single row (dictionary)
    dict_strategy = st.fixed_dictionaries(column_strategies)
    
    # Create a strategy for a list of rows
    list_strategy = st.lists(dict_strategy)
    
    return list_strategy
    

### Debug

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)

# test-views.py

This is a Python file, that you can add to your tests folder. When using `viktor-cli test` it will automatically generate a bunch of params, and test if all your views work, or properly throw a vkt.UserError!

This python file will load your app, and parse the Parametrization to Hypothesis strategies. This will result in a `fixed_dictionaries` strategy, where every value is a strategy on its own. E.g. `NumberField` will map to a `floats` strategy.

The `settings` decorator can be used to draw more examples from the composite strategy.

# Setup

- Download the python file
- Add it to the `tests` folder of any Viktor app
- Run `viktor-cli test`
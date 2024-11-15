## Hathor Scribbler

A CLI utility to help you storing data on Hathor Network. It can add entries to existing tokens
or create new tokens with data.

This follows the data outputs featured [here](https://docs.hathor.network/explanations/features/data-outputs/) 
for traceability use cases.

### Usage

You need to have a wallet headless running. By default, it assumes it's running on port 8080.

```
python3 writer.py
```

#### Dependencies

You need to use python3. The project has some dependencies listed on `requirements.txt`.

It's recommended to use a virtual env to handle dependencies.

```
pip3 install virtualenv
python3 -m venv env
# Now activate the virtual env
source env/bin/activate
# Then install the dependencies
pip3 install -r requirements.txt
```

You can read more here: https://www.freecodecamp.org/news/how-to-setup-virtual-environments-in-python/

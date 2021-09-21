# Nowcasting Api
API for hosting nowcasting solar predictions.  
Will just return 'dummy' numbers until about mid-2022!

The api is using FastAPI - https://fastapi.tiangolo.com/

# Documentation

Documentation can be viewed by going to `/docs`. This is automatically produced from the code.

# Setup

Create a virtual environment
```python3 -m venv ./venv ```

and activate with
``` source venv/activation/bin```

and install the requirements
``` pip install -r requirements.txt ```

# Local start up

Use ```uvicorn main:app --reload ``` 
to start up on a local host

"""Core, UI-independent application logic — shared by the Streamlit app
(streamlit_app.py) and the FastAPI service (api/main.py).

Nothing in this package imports streamlit or fastapi, so it can be used
headless from either front end, a script, or tests.
"""

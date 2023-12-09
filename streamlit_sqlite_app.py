import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

import sys
sys.path.append('./config')
from config import \
    sqlite_db, \
    log_csv_versions_directory

# Set up the page layout
st.set_page_config(layout="wide")

# Function to load data from SQLite database
def load_data(table_name):
    conn = sqlite3.connect(sqlite_db)
    query = f"SELECT * FROM {table_name};"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Function to update a specific cell in the database
def update_database_cell(table_name, unique_id_column, unique_id, column_name, new_value):
    conn = sqlite3.connect(sqlite_db)
    # Enclose the column name and unique_id_column in double quotes for SQL compatibility
    sql = f'UPDATE {table_name} SET "{column_name}" = ? WHERE "{unique_id_column}" = ?'
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (new_value, unique_id))
        conn.commit()
    except Exception as e:
        st.error(f'An error occurred: {e}')
    finally:
        conn.close()

# Load data
iris = load_data('iris')
imdb = load_data('imdb')

# Sidebar for page selection
page = st.sidebar.radio("Choose a Dataset", ('Iris', 'IMDb'))

# Initialize session state for filters, the filter added flag, and the filtered DataFrame
if 'iris_filters' not in st.session_state:
    st.session_state['iris_filters'] = []
if 'imdb_filters' not in st.session_state:
    st.session_state['imdb_filters'] = []
if 'filter_added' not in st.session_state:
    st.session_state['filter_added'] = False
if 'df_filtered' not in st.session_state:
    st.session_state['df_filtered'] = iris if page == 'Iris' else imdb

# Function to apply filters
def apply_filters(df, filters):
    filtered_df = df.copy()
    for f in filters:
        if f['type'] == 'equals':
            filtered_df = filtered_df[filtered_df[f['column']] == f['value']]
        elif f['type'] == 'contains' and filtered_df[f['column']].dtype == object:
            filtered_df = filtered_df[filtered_df[f['column']].str.contains(f['value'])]
        elif f['type'] == 'greater than':
            filtered_df = filtered_df[filtered_df[f['column']] > f['value']]
        elif f['type'] == 'less than':
            filtered_df = filtered_df[filtered_df[f['column']] < f['value']]
    return filtered_df

# Define column configurations for IMDb dataset
imdb_column_config = {
    "text": st.column_config.TextColumn("Text", disabled=True),
    "label": st.column_config.NumberColumn("Label")
}

# Define column configurations for Iris dataset
iris_column_config = {
    "sepal length (cm)": st.column_config.NumberColumn("Sepal Length"),
    "sepal width (cm)": st.column_config.NumberColumn("Sepal Width"),
    "petal length (cm)": st.column_config.NumberColumn("Petal Length"),
    "petal width (cm)": st.column_config.NumberColumn("Petal Width")
}

# Page layout
if page == 'Iris':
    st.title('IRIS')
    df = iris
    filter_key = 'iris_filters'
    column_config = iris_column_config
elif page == 'IMDb':
    st.title('IMDb')
    df = imdb
    filter_key = 'imdb_filters'
    column_config = imdb_column_config

# UI layout common to both pages
# Checkbox for filtering NaNs
if st.checkbox('Show rows with NaNs'):
    df = df[df.isna().any(axis=1)]

# Add a filter
if st.button('Add Filter'):
    st.session_state[filter_key].append({'column': None, 'type': None, 'value': None})
    st.session_state['filter_added'] = True

# Display filters
for i, f in enumerate(list(st.session_state[filter_key])):
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 3, 3, 1])
        with col1:
            f['column'] = st.selectbox('Column', df.columns, key=f'{page}_col_{i}')
        with col2:
            f['type'] = st.selectbox('Filter Type', ['equals', 'contains', 'greater than', 'less than'], key=f'{page}_type_{i}')
        with col3:
            if f['type'] in ['equals', 'contains']:
                f['value'] = st.text_input('Value', key=f'{page}_value_{i}')
            elif f['type'] in ['greater than', 'less than']:
                f['value'] = st.number_input('Value', key=f'{page}_num_{i}')
        with col4:
            if st.button('Remove', key=f'{page}_remove_{i}'):
                del st.session_state[filter_key][i]
                if not st.session_state[filter_key]:
                    st.session_state['filter_added'] = False

# Use session state to maintain the filtered DataFrame
if st.session_state['filter_added']:
    if st.button('Apply Filters'):
        st.session_state['df_filtered'] = apply_filters(df, st.session_state[filter_key])
else:
    st.session_state['df_filtered'] = df

# Display the data editor
df_filtered = st.data_editor(st.session_state['df_filtered'], column_config=column_config, use_container_width=True)

unique_id_mapping = {
    'iris': 'Index',
    'imdb': 'Index_col'
}

# Submit button to update the database
if st.button('Submit Updates'):
    table_name = 'iris' if page == 'Iris' else 'imdb'
    unique_id_column = unique_id_mapping[table_name]
    original_df = load_data(table_name)
    for index, row in df_filtered.iterrows():
        original_row = original_df.loc[index]
        for col in df_filtered.columns:
            if row[col] != original_row[col]:
                update_database_cell(table_name, unique_id_column, row[unique_id_column], col, row[col])

    # Create the directory if it does not exist
    directory = f'{log_csv_versions_directory}/{table_name}'
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Generate a timestamp
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    # Save the DataFrame to a CSV file
    csv_filename = f"{directory}/{table_name}_{timestamp}.csv"
    df_filtered.to_csv(csv_filename, index=False)

    st.success(f'{page} dataset updated successfully in the database and saved to {csv_filename}.')

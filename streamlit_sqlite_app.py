import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

import sys
sys.path.append('./config')
from config import sqlite_db, log_csv_versions_directory

###### HELPER FUNCTIONS | BEGIN #######

# Function to load data from SQLite database
def load_data(table_name):
    conn = sqlite3.connect(sqlite_db)
    query = f"SELECT * FROM {table_name};"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Function to replace table in the database
def replace_table(table_name, df):
    conn = sqlite3.connect(sqlite_db)
    try:
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.commit()
    except Exception as e:
        st.error(f'An error occurred while replacing the table: {e}')
    finally:
        conn.close()

# Function to save DataFrame to CSV in log directory
def save_to_log(df, table_name):
    directory = f'{log_csv_versions_directory}/{table_name}'
    if not os.path.exists(directory):
        os.makedirs(directory)
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    csv_filename = f"{directory}/{table_name}_{timestamp}.csv"
    df.to_csv(csv_filename, index=False)
    return csv_filename

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

# Function to update a specific cell in the database
def update_database_cell(table_name, unique_id_column, unique_id, column_name, new_value):
    conn = sqlite3.connect(sqlite_db)
    sql = f'UPDATE {table_name} SET "{column_name}" = ? WHERE "{unique_id_column}" = ?'
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (new_value, unique_id))
        conn.commit()
    except Exception as e:
        st.error(f'An error occurred: {e}')
    finally:
        conn.close()

###### HELPER FUNCTIONS | END #######

###### STREAMLIT APP | BEGIN #######

# Set up the page layout
st.set_page_config(layout="wide")

# Sidebar for page selection
page = st.sidebar.radio("Choose a Dataset", ('Iris', 'IMDb'))

# Set the filter_key based on the selected page
filter_key = 'iris_filters' if page == 'Iris' else 'imdb_filters'

# Load data
iris = load_data('iris')
imdb = load_data('imdb')

# Define column configurations for Iris dataset
iris_column_config = {
    "Select": st.column_config.CheckboxColumn("Select"),
    "sepal length (cm)": st.column_config.NumberColumn("Sepal Length", format="%.2f"),
    "sepal width (cm)": st.column_config.NumberColumn("Sepal Width", format="%.2f"),
    "petal length (cm)": st.column_config.NumberColumn("Petal Length", format="%.2f"),
    "petal width (cm)": st.column_config.NumberColumn("Petal Width", format="%.2f")
}

# Define column configurations for IMDb dataset
imdb_column_config = {
    "Select": st.column_config.CheckboxColumn("Select"),
    "text": st.column_config.TextColumn("Text"),
    "label": st.column_config.NumberColumn("Label")
}

# Sidebar buttons for actions
if page == 'Iris':
    if st.sidebar.button('Upload Your Own Data', key='sidebar_upload_iris'):
        st.session_state['show_uploader_iris'] = True

    if st.sidebar.button('Refresh Data', key='sidebar_refresh_iris'):
        iris = load_data('iris')
        st.session_state['df_filtered'] = apply_filters(iris, st.session_state.get('iris_filters', []))
        st.experimental_rerun()
    
    column_config = iris_column_config

elif page == 'IMDb':
    if st.sidebar.button('Upload Your Own Data', key='sidebar_upload_imdb'):
        st.session_state['show_uploader_imdb'] = True

    if st.sidebar.button('Refresh Data', key='sidebar_refresh_imdb'):
        imdb = load_data('imdb')
        st.session_state['df_filtered'] = apply_filters(imdb, st.session_state.get('imdb_filters', []))
        st.experimental_rerun()

    column_config = imdb_column_config

# Page layout
st.title(f"{page} Dataset")

# Initialize session state for filters, the filter added flag, and the filtered DataFrame
if 'iris_filters' not in st.session_state:
    st.session_state['iris_filters'] = []
if 'imdb_filters' not in st.session_state:
    st.session_state['imdb_filters'] = []
if 'filter_added' not in st.session_state:
    st.session_state['filter_added'] = False
if 'df_filtered' not in st.session_state:
    st.session_state['df_filtered'] = iris if page == 'Iris' else imdb

# Use session state to maintain the filtered DataFrame
if st.session_state['filter_added']:
    if st.button('Apply Filters'):
        st.session_state['df_filtered'] = apply_filters(st.session_state['df_filtered'], st.session_state[filter_key])
else:
    st.session_state['df_filtered'] = load_data('iris') if page == 'Iris' else load_data('imdb')

# UI layout common to both pages
# Checkbox for filtering NaNs
if st.checkbox('Show rows with NaNs'):
    st.session_state['df_filtered'] = st.session_state['df_filtered'][st.session_state['df_filtered'].isna().any(axis=1)]

if st.checkbox('Show hidden items', value=True):
    st.session_state['df_filtered'] = st.session_state['df_filtered'][st.session_state['df_filtered']['Select'] != True]

# Add a filter
if st.button('Add Filter'):
    st.session_state[filter_key].append({'column': None, 'type': None, 'value': None})
    st.session_state['filter_added'] = True

# Display filters
for i, f in enumerate(list(st.session_state.get(filter_key, []))):
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 3, 3, 1])
        with col1:
            f['column'] = st.selectbox('Column', st.session_state['df_filtered'].columns, key=f'{page}_col_{i}')
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

    # Save the DataFrame to a CSV file
    csv_filename = save_to_log(df_filtered, table_name)
    st.success(f'{page} dataset updated successfully in the database and saved to {csv_filename}.')

# File uploader in the sidebar under the button (for both Iris and IMDb)
if st.session_state.get('show_uploader_iris', False) and page == 'Iris':
    uploaded_file = st.sidebar.file_uploader("Upload a CSV to update the Iris dataset", type="csv", key="sidebar_iris_csv")
    if uploaded_file is not None:
        iris_df = pd.read_csv(uploaded_file)
        replace_table('iris', iris_df)
        csv_filename = save_to_log(iris_df, 'iris')
        iris = load_data('iris')  # Refresh the data
        st.session_state['df_filtered'] = iris
        st.success(f'Iris dataset updated successfully and saved to {csv_filename}.')

if st.session_state.get('show_uploader_imdb', False) and page == 'IMDb':
    uploaded_file = st.sidebar.file_uploader("Upload a CSV to update the IMDb dataset", type="csv", key="sidebar_imdb_csv")
    if uploaded_file is not None:
        imdb_df = pd.read_csv(uploaded_file)
        replace_table('imdb', imdb_df)
        csv_filename = save_to_log(imdb_df, 'imdb')
        imdb = load_data('imdb')  # Refresh the data
        st.session_state['df_filtered'] = imdb
        st.success(f'IMDb dataset updated successfully and saved to {csv_filename}.')

###### STREAMLIT APP | END #######

from dotenv import load_dotenv
import streamlit as st
import os
import re
import json
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.utilities import SQLDatabase
import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain.tools import tool
from pydantic import BaseModel, Field
from langchain.agents.agent import AgentExecutor
from langchain.agents.format_scratchpad.openai_tools import format_to_openai_tool_messages
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain_core.prompts import ChatPromptTemplate, FewShotPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain.chains import create_sql_query_chain
from langchain_community.tools import QuerySQLDatabaseTool

load_dotenv()
db = SQLDatabase.from_uri("sqlite:///physio.db")

try:
    open_ai_key = os.getenv("OPENAI_KEY")
    if not open_ai_key:
        raise ValueError("OPENAI_KEY not found")
    os.environ["OPENAI_API_KEY"] = open_ai_key
except:
    st.write("To use the Chatbot, please include your OpenAI key in a .env file")
else:
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")

    #Few shot prompting
    examples = [
        {
            "input": "List all exercise entries.", 
            "query": "SELECT * FROM physio_table;"
        },
        {
            "input": "Find all exercise entries on '2024-05-02'.",
            "query": "SELECT * FROM physio_table WHERE DATE(Datetime) = '2024-05-02';",
        },
        {
            "input": "List all entries where the exercise count is more than 50.",
            "query": "SELECT * FROM physio_table WHERE count > 50;",
        },
        {
            "input": "Find the total number of exercises performed on '2024-05-01'.",
            "query": "SELECT SUM(count) FROM physio_table WHERE DATE(Datetime) = '2024-05-01';",
        },
        {
            "input": "List all exercise entries where the type is 'Squat'.",
            "query": "SELECT * FROM physio_table WHERE physio_type = 'Squat';",
        },
        {
            "input": "How many exercise entries are there in total?",
            "query": "SELECT COUNT(*) FROM physio_table;",
        },
        {
            "input": "Find the entry with the highest number of exercises recorded.",
            "query": "SELECT * FROM physio_table ORDER BY count DESC LIMIT 1;",
        },
        {
            "input": "List all exercise entries from March 2024.",
            "query": "SELECT * FROM physio_table WHERE strftime('%Y-%m', Datetime) = '2024-03';",
        },
        {
            "input": "Find the average number of exercises performed across all entries.",
            "query": "SELECT AVG(count) FROM physio_table;",
        },
        {
            "input": "How many unique exercise types are recorded?",
            "query": "SELECT COUNT(DISTINCT physio_type) FROM physio_table;",
        },
        {
            "input": "Find the earliest recorded exercise entry.",
            "query": "SELECT * FROM physio_table ORDER BY Datetime ASC LIMIT 1;",
        },
        {
            "input": "List all exercise entries on '2024-03-05' where more than 40 reps were performed.",
            "query": "SELECT * FROM physio_table WHERE DATE(Datetime) = '2024-03-05' AND count > 40;", 
        },
        {
            "input": "How many times did I do push-ups in 2024?",
            "query": "SELECT COUNT(*) FROM physio_table WHERE physio_type = 'Push Up' AND strftime('%Y', Datetime) = '2024';", 
        },
        {
            "input": "Can you create a bar chart of the total exercises performed per day for May 2024?",
            "query": "SELECT DATE(Datetime) AS date, SUM(count) AS total_exercises FROM physio_table WHERE strftime('%Y-%m', Datetime) = '2024-05' GROUP BY DATE(Datetime) ORDER BY DATE(Datetime);", 
        }
    ]


    example_selector = SemanticSimilarityExampleSelector.from_examples(
        examples,
        embedding_model,
        FAISS,
        k=5,
        input_keys=["input"],
    )

    system_prefix = """You are an agent designed to interact with a SQL database.
    Given an input question, create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
    \n\n Return ONLY the SQL query, the response should start with SELECT.
    \n\nUnless otherwise specificed, do not return more than {top_k} rows.
    \n\nHere is the relevant table info: {table_info}
    \n\nBelow are a number of examples of questions and their corresponding SQL queries.
    You can order the results by a relevant column to return the most interesting examples in the database.
    Never query for all the columns from a specific table, only ask for the relevant columns given the question.
    You have access to tools for interacting with the database.
    Only use the given tools. Only use the information returned by the tools to construct your final answer.
    You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

    If you need to filter on a proper noun, you must ALWAYS first look up the filter value using the "search_proper_nouns" tool!

    DO NOT make or run any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

    DO NOT use Limit for any queries relating to data visualisation such as a bar graph, line graph or table.

    Here are some examples of user inputs and their corresponding SQL queries:"""

    example_prompt = PromptTemplate.from_template("User input: {input}\nSQL query: {query}")
    prompt = FewShotPromptTemplate(
        example_selector=example_selector,
        example_prompt=example_prompt,
        prefix=system_prefix,
        suffix="User input: {input}\nSQL query: ",
        input_variables=["input", "top_k", "table_info"],
    )

    write_query = create_sql_query_chain(llm, db, prompt)
    execute_query = QuerySQLDatabaseTool(db=db)
    sql_chain = write_query | execute_query

    class QueryInput(BaseModel):
        query: str = Field(description="""a natural language question that requires a sql query to be 
                        run against the physio_table table, must be the exact same
                            as the user's original question. DO NOT MODIFY IT""")

    @tool("sql_query_db_tool", args_schema=QueryInput)
    def sql_query_db_tool(query):
        """Accepts only one input string that contains the user's natural language question and runs a query against on the
        physio_db and returns a natural language reponse. The question should be the exact same as that as the user's original question.
        """
        return sql_chain.invoke({"question": query})

    class DataInput(BaseModel):
        data: str = Field(description="should be a string that contains data as a list of lists")
        graph: str = Field(description= "it must include what type of graph to be produced, \
                        for instance bar graph, line graph etc")
        columns: str = Field(description="should be a string resembling a list format containing the columns that corresponds to the index of the data eg. '[time, protein, fat]'")
        
        
    @tool("data-visualisation-tool", args_schema=DataInput)
    def data_visualisation_tool(data: str, columns:str, graph: str):
        """Use this tool to visualise a line graph, bar graph or table. Accepts only two input strings, the first containing data and the second, containing the type of graph for data visualisation, and produces a visualisation. This tool returns None 
        as it generates a graph in streamlit. This tool must only be run a maximum of one time, even if there is a mistake and should only be run after running the sql_db_query tool"""
        template_str =  """
            You are a JSON expert designed to handle an incoming data, and reproduce the data in a JSON format. You MUST respond starting with the JSON bracket. So all responses must start with "{".
            Let's decode the way to respond to the data. The responses depend on the type of information requested in the data. Format the column names regards to the original query.
            
            1. If the data requires a table, format your answer like this:
            {
                "table": {
                    "columns": ["Date", "Squats", "Push Up"],
                    "data": [
                        ["03-04-2024", 30, 21],
                        ["13-05-2024", 25, 20]
                    ]
                }
            }

            2. For a bar chart, respond like this:
            {
                "bar": {
                    "columns": ["Date", "Squats", "Push Up"],
                    "data": [
                        ["03-04-2024", 30, 21],
                        ["03-05-2024", 25, 20]
                    ]
                }
            }

            3. If a line chart is more appropriate, your reply should look like this:
            {
                "line": {
                    "columns": ["Date", "Squats", "Push Up"],
                    "data": [
                        ["03-04-2024", 30, 21],
                        ["03-05-2024", 25, 20]
                    ]
                }
            }
            
            For graphs with only two variables, format it like so:
                {
                "line": {
                    "columns": ["Squats", "Push Up"],
                    "data": [
                        [30, 21],
                        [25, 20]
                    ]
                }
            }

            Note: We only accommodate two types of charts: "bar" and "line".

            4. If the answer is not known or available or cannot be represented with a table, line graph or bar graph, respond with:
            {"answer": "A graph is incomptabile with the query."}

            Return all output as a string. Remember to encase all strings in the "columns" list and data list in double quotes for JSON formatting.
            ix the date to be %dd-%mm-%yyyy. So January 13 2024 should be 01-13-2024 and not 13-01-2024. Do not truncate the data! 
            The final JSON should not be left cut like ["01-21-202 and must be fully finished.
            
            If there is date in the columns, priotise it to be the first index in the list in columns. 
            Likewise is the user specifies an x-axis, priotise it to be in the front of the list in 
            coloumns. Y-axis columns should be kept to the back of the list. Decide on the data
            to assign either x-axis or y-axis to the columns. If the query is of the format Y against X, 
            then it should be ordered y-axis against x-axis.
            
            With the above instructions in mind, given the following user question, corresponding data,
            generate a string in the above format to visualise data using pandas.
            """
        template = ChatPromptTemplate.from_messages([
        SystemMessage(content=template_str),
        ("human", "Hello, this is my data: {data}, with the following columns {columns}, and the following graph conditions {graph} in response to this question {query}. Please format it according to the instructions")]
        )
        chain = template | llm | StrOutputParser()
        response = chain.invoke({"data": data, "graph": graph, "query":user_input, "columns": columns})
        try:
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                json_str = match.group(0)
                response_dict = json.loads(json_str)
            else:
                print("No JSON found in response.")
        except json.JSONDecodeError as e:
            print(json_str)
            st.write(f"JSON decoding failed: {e}")
        else:
            # Check if the response is a textual answer.
            if "answer" in response_dict:
                st.write(response_dict["answer"])
            
            # Check if the response is a bar chart.
            if "bar" in response_dict:
                try:
                    columns = response_dict["bar"]["columns"]
                    data = response_dict["bar"]["data"]
                    # Create the DataFrame
                    df = pd.DataFrame(data, columns=columns)

                    # Convert 'Date' to datetime format
                    try:
                        df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
                    except ValueError as e:
                        df['Date'] = pd.to_datetime(df['Date'], format='%m-%d-%Y')

                    # Convert other columns to float
                    for col in df.columns:
                        if col != 'Date':
                            df[col] = pd.to_numeric(df[col])

                    # Set the index
                    x_axis = columns[0]
                    y_axis = ", ".join(columns[1:])
                    df.set_index(x_axis, inplace=True)
                    
                    # Display the bar chart
                    st.bar_chart(data = df, x_label = x_axis, y_label = y_axis)

                except Exception as e:
                    st.error(f"Error processing data: {e}")

            # Check if the response is a line chart.
            if "line" in response_dict:
                try:
                    columns = response_dict["line"]["columns"]
                    data = response_dict["line"]["data"]

                    # Create the DataFrame
                    df = pd.DataFrame(data, columns=columns)

                    # Convert 'Date' to datetime format
                    try:
                        df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
                    except ValueError as e:
                        df['Date'] = pd.to_datetime(df['Date'], format='%m-%d-%Y')
                    # Convert other columns to float
                    for col in df.columns:
                        if col != 'Date':
                            df[col] = pd.to_numeric(df[col])

                    # Set the index
                    x_axis = columns[0]
                    y_axis = ", ".join(columns[1:])
                    df.set_index(x_axis, inplace=True)
                    
                    # Display the line chart
                    st.line_chart(data = df, x_label = x_axis, y_label = y_axis)

                except Exception as e:
                    st.error(f"Error processing data: {e}")

            # Check if the response is a table.
            if "table" in response_dict:
                columns = response_dict["table"]["columns"]
                data = response_dict["table"]["data"]
                df = pd.DataFrame(data, columns=columns)
                st.table(df)

    tools = [data_visualisation_tool, sql_query_db_tool]

    llm_with_tools = llm.bind_tools(tools)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are very powerful assistant chatbot to help people exercise healthier. You have access to tools
                to query a user's exercise database named physio_table and to turn that data into a visualisation chart. When using sql_query_tool_db, DO NOT MODIFY THE ORIGINAL QUESTION.
                If the user fails to specify a specific time frame for data visualisation, the default time frame would be per day. For instance,
                'Create a line chart of the number of squats I did in 2024' should be reformatted to 'Create a line chart of the number of squats I did in 2024 per day'
                before being passed to sql_query_db_tool. If the user wants to create a data visualisation chart, run sql_query_tool_db first to get
                the data before running data_visualisation tool to visualise the data. To use data_visualisation_tool, you must give two inputs, one for the 
                data and one for the type of graph. Additionally, you must pass on all the data given by the sql_db_query_tool and the data must not be
                abbreviated by ... or other means. Every single data point, regardless of the quantity must be passed on to the data visualisation tool.
                Additionally, if bar chart or line chart or table is required by the user, you must pass data into data_visualization tool""",
            ),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )
            
    agent = (
        {
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                x["intermediate_steps"]
            ),
        }
        | prompt
        | llm_with_tools
        | OpenAIToolsAgentOutputParser()
    )

    agent_executor = AgentExecutor(
        agent=agent,
        verbose=True,
        tools=tools
    )

    import streamlit as st

    st.set_page_config(page_title="ChatBot", layout="centered")

    st.title("💬 ChatBot")
    st.write("Ask any question related to your exercise history!")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # User input
    user_input = st.chat_input("Type your message here...")

    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Display user message
        with st.chat_message("user"):
            st.write(user_input)

        # Generate response
        with st.spinner("Thinking..."):
            response = agent_executor.invoke({"input": user_input})["output"]

        # Add bot response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Display bot response
        with st.chat_message("assistant"):
            st.write(response)
        

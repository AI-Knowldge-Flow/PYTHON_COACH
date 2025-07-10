
#  AWESOME GOLDEN VERSION - DO NOT MODIFY DO NOT MODIFY DO NOT MODIFY
#DO NOT MODIFY
# Uploaded to git

# Python Coach - Complete Application with SQLite3 Database Support and Plot Display Feature

import streamlit as st
import anthropic
import os
import sqlite3
import json
import time
import sys
import matplotlib.pyplot as plt
import numpy as np
from io import StringIO, BytesIO
import base64
import contextlib
from datetime import datetime
from dotenv import load_dotenv
from functools import wraps

# Load environment variables from .env file
load_dotenv()


# Database setup and management
class DatabaseManager:
    def __init__(self, db_path="python_coach.db"):
        """Initialize database manager with given database path"""
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize the database with necessary tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create lessons table
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS lessons
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           topic
                           TEXT
                           NOT
                           NULL,
                           difficulty
                           TEXT,
                           content
                           TEXT,
                           code_blocks
                           TEXT,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       ''')

        # Create user_practice table
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS user_practice
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           lesson_id
                           INTEGER,
                           code
                           TEXT,
                           last_modified
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           lesson_id
                       ) REFERENCES lessons
                       (
                           id
                       )
                           )
                       ''')

        conn.commit()
        conn.close()

    def save_lesson(self, topic, difficulty, content, code_blocks):
        """Save a generated lesson to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Convert code_blocks list to JSON string for storage
        code_blocks_json = json.dumps(code_blocks)

        cursor.execute(
            "INSERT INTO lessons (topic, difficulty, content, code_blocks) VALUES (?, ?, ?, ?)",
            (topic, difficulty, content, code_blocks_json)
        )

        # Get the ID of the newly inserted lesson
        lesson_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return lesson_id

    def get_lesson(self, lesson_id):
        """Retrieve a lesson by its ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,))
        lesson = cursor.fetchone()

        conn.close()

        if lesson:
            # Convert columns to a dictionary
            lesson_dict = {
                "id": lesson[0],
                "topic": lesson[1],
                "difficulty": lesson[2],
                "content": lesson[3],
                "code_blocks": json.loads(lesson[4]),
                "created_at": lesson[5]
            }
            return lesson_dict
        return None

    def get_all_lessons(self):
        """Retrieve all lessons with basic information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, topic, difficulty, created_at FROM lessons ORDER BY created_at DESC")
        lessons = cursor.fetchall()

        conn.close()

        result = []
        for lesson in lessons:
            result.append({
                "id": lesson[0],
                "topic": lesson[1],
                "difficulty": lesson[2],
                "created_at": lesson[3]
            })

        return result

    def save_practice_code(self, lesson_id, code):
        """Save user's practice code associated with a lesson"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if practice entry already exists
        cursor.execute("SELECT id FROM user_practice WHERE lesson_id = ?", (lesson_id,))
        existing = cursor.fetchone()

        if existing:
            # Update existing practice
            cursor.execute(
                "UPDATE user_practice SET code = ?, last_modified = CURRENT_TIMESTAMP WHERE lesson_id = ?",
                (code, lesson_id)
            )
        else:
            # Create new practice entry
            cursor.execute(
                "INSERT INTO user_practice (lesson_id, code) VALUES (?, ?)",
                (lesson_id, code)
            )

        conn.commit()
        conn.close()

    def get_practice_code(self, lesson_id):
        """Retrieve user's practice code for a specific lesson"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT code FROM user_practice WHERE lesson_id = ?", (lesson_id,))
        result = cursor.fetchone()

        conn.close()

        if result:
            return result[0]
        return None


# Function to execute Python code safely with plot capture
@contextlib.contextmanager
def capture_output():
    """Context manager to capture stdout and stderr"""
    old_stdout, old_stderr = sys.stdout, sys.stderr
    stdout_buffer = StringIO()
    stderr_buffer = StringIO()
    sys.stdout, sys.stderr = stdout_buffer, stderr_buffer
    try:
        yield stdout_buffer, stderr_buffer
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr


def execute_code(code, capture_plots=True):
    """Execute Python code in a safe environment and return the output and plots"""
    # Replace plt.show() calls in the code with plt.close() or remove them
    if capture_plots:
        # Simple string replacement to handle common show() patterns
        modified_code = code
        # Replace common plt.show() patterns
        show_patterns = [
            "plt.show()",
            "plt.show( )",
            "matplotlib.pyplot.show()",
            "matplotlib.pyplot.show( )"
        ]
        for pattern in show_patterns:
            modified_code = modified_code.replace(pattern, "# plt.show() - removed for Streamlit compatibility")
    else:
        modified_code = code
    
    with capture_output() as (stdout_buffer, stderr_buffer):
        plots = []
        if capture_plots:
            # Store the current figure objects
            plt.close('all')  # Close any existing figures first
            old_figs = plt.get_fignums()
            
        try:
            # Execute the modified code in a restricted environment
            # Create a copy of globals with necessary imports for plotting
            globals_dict = {
                "__builtins__": __builtins__,
                "plt": plt,
                "np": np,
                "matplotlib": __import__('matplotlib')
            }
            
            # Execute with the enhanced globals
            exec(modified_code, globals_dict)
            output = stdout_buffer.getvalue()
            error = stderr_buffer.getvalue()
            
            # Filter out the specific warning about FigureCanvasAgg
            error_lines = error.split('\n')
            filtered_error_lines = [line for line in error_lines if "FigureCanvasAgg is non-interactive" not in line]
            filtered_error = '\n'.join(filtered_error_lines)
            
            # Capture any matplotlib plots if enabled
            if capture_plots:
                # Get new figures created by the code
                new_figs = plt.get_fignums()
                new_fig_nums = set(new_figs) - set(old_figs)
                
                # Convert each new figure to an image
                for fig_num in new_fig_nums:
                    try:
                        fig = plt.figure(fig_num)
                        buf = BytesIO()
                        fig.savefig(buf, format='png', bbox_inches='tight')
                        buf.seek(0)
                        img_str = base64.b64encode(buf.read()).decode()
                        plots.append(img_str)
                    except Exception as plot_error:
                        # If plot capture fails, add the error to the output
                        filtered_error += f"\nError capturing plot: {str(plot_error)}"
                
            if filtered_error:
                return False, filtered_error, plots
            return True, output, plots
        except Exception as e:
            return False, str(e), plots
        finally:
            if capture_plots:
                # Always close all figures to avoid memory issues
                plt.close('all')


# Extract code blocks from markdown
def extract_code_blocks(markdown_text):
    """Extract Python code blocks from markdown text"""
    code_blocks = []
    lines = markdown_text.split('\n')
    in_code_block = False
    current_block = []

    for line in lines:
        if line.strip().startswith("```python"):
            in_code_block = True
            current_block = []
        elif line.strip() == "```" and in_code_block:
            in_code_block = False
            code_blocks.append('\n'.join(current_block))
        elif in_code_block:
            current_block.append(line)

    return code_blocks


# Initialize database
db_manager = DatabaseManager()

# Initialize session state variables if they don't exist
if 'full_response' not in st.session_state:
    st.session_state.full_response = ""

if 'practice_code' not in st.session_state:
    st.session_state.practice_code = """# Write your Python code here
# Example:
name = "Python Learner"
print(f"Hello, {name}!")

# Try creating variables, loops, or functions
for i in range(5):
    print(f"Count: {i}")
"""

if 'code_blocks' not in st.session_state:
    st.session_state.code_blocks = []

if 'selected_topic' not in st.session_state:
    st.session_state.selected_topic = ""

if 'current_lesson_id' not in st.session_state:
    st.session_state.current_lesson_id = None

if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Learn Python"

# Add plot display toggle to session state
if 'show_plots' not in st.session_state:
    st.session_state.show_plots = True

# Set page configuration
st.set_page_config(
    page_title="Python Coach",
    page_icon="🐍",
    layout="wide"
)

# Initialize Anthropic client with API key
client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Page title and description
st.title("🐍 Python Coach")
st.markdown("""
This app uses Claude Sonnet to teach Python to beginners.
Enter a programming concept or task you'd like to learn, and Claude will generate well-formatted Python code with explanations.
You can also execute the code examples directly in the app!
""")

# Create tabs for different sections
tab1, tab2 = st.tabs(["Learn Python", "Practice Coding"])

# LEARN PYTHON TAB
with tab1:
    # Create sidebar with options
    with st.sidebar:
        st.header("Options")
        difficulty = st.select_slider(
            "Difficulty Level",
            options=["Beginner", "Intermediate", "Advanced"],
            value="Beginner"
        )

        include_comments = st.checkbox("Include detailed comments", value=True)
        include_explanation = st.checkbox("Include explanation", value=True)
        run_examples = st.checkbox("Include runnable examples", value=True)

        # Add plot display toggle
        st.divider()
        st.header("Display Settings")
        show_plots = st.checkbox("Show plots after code execution", value=st.session_state.show_plots)

        # Update session state when value changes
        if show_plots != st.session_state.show_plots:
            st.session_state.show_plots = show_plots

        st.divider()

        # Add lesson history section to sidebar
        st.header("Lesson History")
        lessons = db_manager.get_all_lessons()

        if lessons:
            st.write("Your previous lessons:")
            for lesson in lessons:
                if st.button(f"{lesson['topic']} ({lesson['difficulty']})", key=f"lesson_{lesson['id']}"):
                    # Load the selected lesson
                    full_lesson = db_manager.get_lesson(lesson['id'])
                    st.session_state.full_response = full_lesson['content']
                    st.session_state.code_blocks = full_lesson['code_blocks']
                    st.session_state.current_lesson_id = lesson['id']
                    st.session_state.selected_topic = lesson['topic']
                    st.rerun()
        else:
            st.write("No lesson history yet.")

        st.divider()
        st.markdown("### About")
        st.markdown("Python Coach is powered by Anthropic's Claude Sonnet 4")

        # Add API key input
        st.divider()
        api_key = st.text_input("Anthropic API Key", type="password", help="Enter your Anthropic API key")
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
            client = anthropic.Anthropic(api_key=api_key)

    # Main content area
    query = st.text_area("What Python concept or task would you like to learn?", height=100)

    # Display current lesson content if available
    if st.session_state.full_response:
        lesson_placeholder = st.empty()
        lesson_placeholder.markdown(st.session_state.full_response)

        # Show code blocks if available
        if st.session_state.code_blocks:
            st.subheader("Run Code Examples")
            st.markdown("Select a code block to execute:")

            for i, code in enumerate(st.session_state.code_blocks, 1):
                with st.expander(f"Code Block {i}"):
                    st.code(code, language="python")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"Execute Code {i}", key=f"exec_{i}"):
                            success, output, plots = execute_code(code, capture_plots=st.session_state.show_plots)
                            if success:
                                st.success("Code executed successfully!")
                                st.code(output, language="text")

                                # Display any generated plots
                                if st.session_state.show_plots and plots:
                                    st.subheader("Generated Plots")
                                    for j, plot_img in enumerate(plots):
                                        st.image(f"data:image/png;base64,{plot_img}", caption=f"Plot {j + 1}")
                            else:
                                st.error(f"Error: {output}")
                    with col2:
                        if st.button(f"Practice with this code {i}", key=f"practice_{i}"):
                            # Save this code to session state and database
                            st.session_state.practice_code = code
                            if st.session_state.current_lesson_id:
                                db_manager.save_practice_code(st.session_state.current_lesson_id, code)

                            # Switch to practice tab
                            st.session_state.active_tab = "Practice Coding"
                            st.rerun()

        # Add button to go to practice
        if st.button("Go to Practice Tab"):
            st.session_state.active_tab = "Practice Coding"
            st.rerun()

    if st.button("Generate Lesson", type="primary"):
        if not os.getenv("ANTHROPIC_API_KEY") and not api_key:
            st.error("Please enter an Anthropic API key in the sidebar.")
        elif not query:
            st.warning("Please enter a Python concept or task to learn.")
        else:
            # Save the query to session state
            st.session_state.selected_topic = query

            # Display a spinner while generating content
            with st.spinner("Generating your Python lesson..."):
                # Prepare the prompt based on user selections
                prompt = f"""You are an expert Python programming coach, teaching a {difficulty.lower()} level student.

                Provide a lesson on: {query}

                Follow these guidelines:
                - Write clean, modern, and idiomatic Python code
                - {"Include detailed comments that explain what each line does" if include_comments else "Include minimal comments"}
                - {"Provide a thorough explanation of the concepts" if include_explanation else "Keep explanations brief"}
                - {"Include runnable examples that demonstrate the concept" if run_examples else "Focus on the core concept without examples"}
                - Format code blocks with proper Python syntax highlighting
                - Ensure your explanations are beginner-friendly and avoid jargon
                - Include common pitfalls or mistakes to avoid
                - Make sure all your code examples are complete and can be executed independently
                - Avoid using external libraries unless absolutely necessary for the concept
                """

                # Create a placeholder for the streaming output
                response_placeholder = st.empty()
                full_response = ""

                try:
                    # Stream the response from Claude
                    with client.messages.stream(
                            model="claude-4-sonnet-20250514",
                            max_tokens=4000,
                            temperature=0.3,
                            system="You are an expert Python programming coach. Your goal is to teach Python concepts clearly with well-formatted, executable code examples. Include helpful comments and explanations appropriate for beginners.",
                            messages=[
                                {"role": "user", "content": prompt}
                            ]
                    ) as stream:
                        for text in stream.text_stream:
                            full_response += text
                            response_placeholder.markdown(full_response)
                            time.sleep(0.01)  # Small delay for smoother streaming visual

                    # Save the full response to session state
                    st.session_state.full_response = full_response

                    # Extract code blocks and save to session state
                    code_blocks = extract_code_blocks(full_response)
                    st.session_state.code_blocks = code_blocks

                    # Save lesson to database
                    lesson_id = db_manager.save_lesson(
                        topic=query,
                        difficulty=difficulty,
                        content=full_response,
                        code_blocks=code_blocks
                    )

                    # Store the current lesson ID in session state
                    st.session_state.current_lesson_id = lesson_id

                    # Display success message
                    st.success("Lesson generated and saved successfully!")

                    # Rerun the app to show the new lesson and code blocks
                    st.rerun()

                except Exception as e:
                    st.error(f"An error occurred: {e}")

# PRACTICE CODING TAB
with tab2:
    st.header("Practice Python Coding")

    # Show the topic being practiced if available
    if st.session_state.selected_topic:
        st.markdown(f"**Currently learning:** {st.session_state.selected_topic}")

    # Show a dropdown of available lessons if any
    lessons = db_manager.get_all_lessons()
    if lessons:
        selected_lesson = st.selectbox(
            "Select a lesson to practice:",
            options=[lesson['id'] for lesson in lessons],
            format_func=lambda x: next((l['topic'] for l in lessons if l['id'] == x), ""),
            key="practice_lesson_select",
            index=0 if st.session_state.current_lesson_id is None else
            next((i for i, l in enumerate(lessons) if l['id'] == st.session_state.current_lesson_id), 0)
        )

        if selected_lesson:
            # Load the selected lesson info
            lesson = db_manager.get_lesson(selected_lesson)
            st.session_state.current_lesson_id = selected_lesson
            st.session_state.selected_topic = lesson['topic']

            # Check if there's existing practice code for this lesson
            existing_practice = db_manager.get_practice_code(selected_lesson)
            if existing_practice:
                st.session_state.practice_code = existing_practice

            # If there are code blocks from the lesson, show a dropdown to select one
            if lesson['code_blocks']:
                st.markdown("**Code examples from this lesson:**")
                selected_block = st.selectbox(
                    "Select a code example:",
                    options=range(len(lesson['code_blocks'])),
                    format_func=lambda x: f"Example {x + 1}",
                    key="selected_block"
                )

                if st.button("Load Selected Example"):
                    st.session_state.practice_code = lesson['code_blocks'][selected_block]
                    # Save to database
                    db_manager.save_practice_code(selected_lesson, lesson['code_blocks'][selected_block])
                    st.rerun()

    st.markdown("""
    Use this area to practice writing and running your own Python code. 
    Try applying what you've learned in the lessons to solve problems or experiment with new concepts.
    """)

    # Create columns for code editor and output
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("Code Editor")

        # Code editor with syntax highlighting
        user_code = st.text_area(
            "Edit code below:",
            value=st.session_state.practice_code,
            height=400,
            key="code_editor"
        )

        # Save code to session state when it changes
        if st.session_state.practice_code != user_code:
            st.session_state.practice_code = user_code
            # Auto-save to database if lesson is selected
            if st.session_state.current_lesson_id:
                db_manager.save_practice_code(st.session_state.current_lesson_id, user_code)

        # Buttons for running code and clearing editor
        col1a, col1b, col1c = st.columns(3)
        with col1a:
            run_button = st.button("Run Code", type="primary", key="run_practice")
        with col1b:
            save_button = st.button("Save Code", key="save_code")
            if save_button and st.session_state.current_lesson_id:
                db_manager.save_practice_code(st.session_state.current_lesson_id, user_code)
                st.success("Code saved successfully!")
        with col1c:
            if st.button("Clear Editor", key="clear_editor"):
                st.session_state.practice_code = "# Write your Python code here\n"
                if st.session_state.current_lesson_id:
                    db_manager.save_practice_code(st.session_state.current_lesson_id, "# Write your Python code here\n")
                st.rerun()

    with col2:
        st.subheader("Output")
        output_area = st.empty()

        # Return to lesson button
        if st.session_state.current_lesson_id:
            if st.button("Return to Lesson", key="return_lesson"):
                st.session_state.active_tab = "Learn Python"
                st.rerun()

        # Run the code when the button is clicked
        if run_button:
            success, result, plots = execute_code(user_code, capture_plots=st.session_state.show_plots)
            if success:
                output_area.success("Code executed successfully!")
                if result.strip():
                    st.text_area("Program Output:", result, height=300, key="output")
                else:
                    st.info("Your code ran but didn't produce any output.")

                # Display any generated plots
                if st.session_state.show_plots and plots:
                    st.subheader("Generated Plots")
                    for i, plot_img in enumerate(plots):
                        st.image(f"data:image/png;base64,{plot_img}", caption=f"Plot {i + 1}")
            else:
                output_area.error("Error executing code:")
                st.text_area("Error details:", result, height=300, key="error")

    # Code examples section
    with st.expander("Starter Code Examples"):
        st.markdown("### Choose a starter template to begin practicing:")

        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("Hello World Example"):
                new_code = """# Simple Hello World program
print("Hello, World!")

# Try changing the message or adding your name
name = "Python Coder"
print(f"Hello, {name}!")
"""
                st.session_state.practice_code = new_code
                if st.session_state.current_lesson_id:
                    db_manager.save_practice_code(st.session_state.current_lesson_id, new_code)
                st.rerun()

            if st.button("Loops Example"):
                new_code = """# For loop example
print("Counting from 1 to 5:")
for i in range(1, 6):
    print(f"Count: {i}")

# Try creating your own loop!
# For example, a countdown from 10 to 1:
print("\\nCountdown:")
for i in range(10, 0, -1):
    print(i)
print("Blast off! 🚀")
"""
                st.session_state.practice_code = new_code
                if st.session_state.current_lesson_id:
                    db_manager.save_practice_code(st.session_state.current_lesson_id, new_code)
                st.rerun()

            # Add a Matplotlib example button
            if st.button("Matplotlib Example"):
                new_code = """# Simple Matplotlib plotting example
import matplotlib.pyplot as plt
import numpy as np

# Generate some data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create a figure and plot the data
plt.figure(figsize=(8, 4))
plt.plot(x, y, 'b-', label='sin(x)')
plt.title('Simple Sine Wave')
plt.xlabel('x')
plt.ylabel('sin(x)')
plt.grid(True)
plt.legend()

# No plt.show() needed - Streamlit will display the figure automatically
"""
                st.session_state.practice_code = new_code
                if st.session_state.current_lesson_id:
                    db_manager.save_practice_code(st.session_state.current_lesson_id, new_code)
                st.rerun()

        with col_b:
            if st.button("Functions Example"):
                new_code = """# Function example
def greet(name):
    return f"Hello, {name}!"

# Call the function
message = greet("Python Learner")
print(message)

# Try creating your own function!
# For example, a function that calculates the square of a number:
def square(number):
    return number ** 2

# Test your function
for num in range(1, 6):
    print(f"The square of {num} is {square(num)}")
"""
                st.session_state.practice_code = new_code
                if st.session_state.current_lesson_id:
                    db_manager.save_practice_code(st.session_state.current_lesson_id, new_code)
                st.rerun()

            if st.button("Lists Example"):
                new_code = """# Lists example
fruits = ["apple", "banana", "orange", "grape"]

# Print the list
print("My fruit list:", fruits)

# Access items
print("First fruit:", fruits[0])
print("Last fruit:", fruits[-1])

# Loop through the list
print("\\nAll fruits:")
for fruit in fruits:
    print(f"- {fruit}")

# Try modifying the list!
# For example, add your favorite fruit:
fruits.append("strawberry")
print("\\nUpdated list:", fruits)
"""
                st.session_state.practice_code = new_code
                if st.session_state.current_lesson_id:
                    db_manager.save_practice_code(st.session_state.current_lesson_id, new_code)
                st.rerun()

            # Add a more complex plotting example
            if st.button("Advanced Plot Example"):
                new_code = """# Advanced Matplotlib example with multiple plots
import matplotlib.pyplot as plt
import numpy as np

# Create a figure with 2 subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

# Generate data
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# First subplot - sin(x)
ax1.plot(x, y1, 'b-', linewidth=2)
ax1.set_title('Sine Function')
ax1.set_ylabel('sin(x)')
ax1.grid(True)

# Second subplot - cos(x)
ax2.plot(x, y2, 'r-', linewidth=2)
ax2.set_title('Cosine Function')
ax2.set_xlabel('x')
ax2.set_ylabel('cos(x)')
ax2.grid(True)

# Adjust spacing between subplots
plt.tight_layout()

# Plot will be automatically displayed in the app
"""
                st.session_state.practice_code = new_code
                if st.session_state.current_lesson_id:
                    db_manager.save_practice_code(st.session_state.current_lesson_id, new_code)
                st.rerun()

    # Practice challenge section
    with st.expander("Practice Challenges"):
        st.markdown("""
        ### Try these coding challenges to test your skills:

        1. **Beginner**: Write a program that prints the even numbers from 1 to 20.

        2. **Beginner**: Create a program that asks for the user's name and age, then prints a greeting that includes how old they'll be next year.

        3. **Intermediate**: Write a function that checks if a word is a palindrome (reads the same forward and backward).

        4. **Intermediate**: Create a program that generates a list of the first 10 Fibonacci numbers.

        5. **Advanced**: Write a function that counts the frequency of each word in a given string and returns a dictionary with the results.

        6. **Data Visualization**: Create a bar chart showing the population of 5 different countries using matplotlib.

        Select a challenge to load it into the editor:
        """)

        # Challenge templates
        challenges = {
            "Even Numbers": """# Challenge: Print all even numbers from 1 to 20
# Write your solution below

# Hint: You can use a for loop and the modulo operator (%)
# Example: if number % 2 == 0, then the number is even

""",
            "Name and Age": """# Challenge: Ask for name and age, then print greeting with next year's age
# Write your solution below

# Hint: Use input() function to get user input
# Example: name = input("Enter your name: ")
# Don't forget to convert age to an integer with int()

""",
            "Palindrome": """# Challenge: Check if a word is a palindrome
# Write your solution below

# Hint: A palindrome reads the same forward and backward
# Examples: "radar", "level", "madam"
# You might want to use string slicing with [::-1]

""",
            "Fibonacci": """# Challenge: Generate the first 10 Fibonacci numbers
# Write your solution below

# Hint: Fibonacci sequence starts with 0, 1
# Each subsequent number is the sum of the two preceding ones
# Example: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34

""",
            "Word Frequency": """# Challenge: Count word frequency in a string
# Write your solution below

# Hint: You can split a string into words with string.split()
# Use a dictionary to count occurrences
# Example: {"hello": 2, "world": 1}

""",
            "Data Visualization": """# Challenge: Create a bar chart showing population data
import matplotlib.pyplot as plt
import numpy as np

# Sample data - replace with your own
countries = ["USA", "China", "India", "Brazil", "Russia"]
populations = [331, 1441, 1380, 212, 145]  # in millions

# Write your code below to create a bar chart of this data
# Hint: Use plt.bar() function

"""
        }

        # Challenge buttons
        col_c, col_d = st.columns(2)
        with col_c:
            if st.button("Even Numbers Challenge"):
                new_code = challenges["Even Numbers"]
                st.session_state.practice_code = new_code
                if st.session_state.current_lesson_id:
                    db_manager.save_practice_code(st.session_state.current_lesson_id, new_code)
                st.rerun()

            if st.button("Palindrome Challenge"):
                new_code = challenges["Palindrome"]
                st.session_state.practice_code = new_code
                if st.session_state.current_lesson_id:
                    db_manager.save_practice_code(st.session_state.current_lesson_id, new_code)
                st.rerun()

            if st.button("Word Frequency Challenge"):
                new_code = challenges["Word Frequency"]
                st.session_state.practice_code = new_code
                if st.session_state.current_lesson_id:
                    db_manager.save_practice_code
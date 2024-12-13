""" Auto GPT. A WIP butler for GPT-4o """

import os
import fnmatch
import subprocess
import json
import requests
import openai
import pyttsx3
import dotenv

# === System Setup ===

dotenv.load_dotenv()

# === Constants ===

OPEN_AI_API_KEY = os.getenv("OPENAI_API_KEY", None)


# === AutoGPT Class ===


class AutoGPT:
    """
    An enhanced version of the ChatGPT module with additional capabilities.

    This module supports structured commands for various operations like file I/O,
    network operations, and system commands. It also maintains a memory of the
    conversation history to generate more context-aware responses.

    """

    def __init__(self):
        self.memory = []  # To store conversation history
        self.local_debug = True  # Set to True to run locally without OpenAI API
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = (
            None
            if self.local_debug
            else openai.Client(api_key=self.api_key, organization="AutoGPT")
        )
        self.tts = pyttsx3.init()

        self.first_message_to_api = (
            "Hello! You are a bot that can execute structured commands.\n"
            "You can interact with files, directories, URLs, and execute shell commands.\n"
            "You can also save and retrieve information from memory.\n"
            "Here is a list of commands you can use:\n"
            "SAY, READ, SAVE, LIST, DELETE, FETCH, EXECUTE, APPEND, SEARCH, CLEAR_MEMORY, MEMORY.\n"
            "You must respond with a structured command for me to execute.\n"
            "Examples:\n"
            '[SAY:"Hello, how are you?"] Will use TextToSpeech to convey the message to the user. '
            "And returns the response by the user.\n"
            '[READ:"file.txt"] Will read the contents of the file. and return it to you.\n'
            '[SAVE:"file.txt":"Hello, how are you?"] Will save the content to the file.\n'
            '[LIST:"directory"] Will list the files in the directory.\n'
            '[DELETE:"file.txt"] Will delete the file.\n'
            '[FETCH:"https://example.com"] Will fetch the content from the URL.\n'
            '[EXECUTE:"ls -l"] Will execute the shell command.\n'
            '[APPEND:"file.txt":"Hello, how are you?"] Will append the content to the file.\n'
            '[SEARCH:"directory":"*.txt"] Will search for files in the directory.\n'
            "[CLEAR_MEMORY] Will clear the conversation history.\n"
            "Please respond with a structured command. Only one command per response.\n"
            "Now start of by using the SAY command to greet me. and await my instructions."
        )

        # print(self.first_message_to_api)

    def process_command(self, command: str) -> str:
        """Process a structured command and execute the corresponding action."""

        command_len = len(command)
        command_blurb = command[: min(command_len, 100)]
        try:
            keyword, arg1, arg2 = self._parse_command(command)
            # print(f"Processing command: {command_blurb}")
            if keyword == "SAY":
                return self.say_tts(command)
            elif keyword == "CLEAR_MEMORY":
                return self._clear_memory()
            elif keyword == "READ":
                return self._read_file(arg1)
            elif keyword == "SAVE":
                return self._save_file(arg1, arg2)
            elif keyword == "LIST":
                return self._list_directory(arg1)
            elif keyword == "DELETE":
                return self._delete_file(arg1)
            elif keyword == "FETCH":
                return self._fetch_url(arg1)
            elif keyword == "EXECUTE":
                return self._execute_command(arg1)
            elif keyword == "APPEND":
                return self._append_to_file(arg1, arg2)
            elif keyword == "SEARCH":
                return self._search_files(arg1, arg2)
            else:
                return f"Invalid command: {keyword} not supported."
        except ValueError as ve:
            print(f"ValueError processing command: {ve}")
            return (
                f"ValueError processing given command: {ve}.\nCommand: {command_blurb}"
            )
        except FileNotFoundError as fnfe:
            print(f"FileNotFoundError processing command: {fnfe}")
            return f"FileNotFoundError processing given command: {fnfe}.\nCommand: {command_blurb}"
        except NotADirectoryError as nde:
            print(f"NotADirectoryError processing command: {nde}")
            return f"NotADirectoryError processing given command: {nde}.\nCommand: {command_blurb}"
        except RuntimeError as re:
            print(f"RuntimeError processing command: {re}")
            return f"RuntimeError processing given command: {re}.\nCommand: {command_blurb}"
        except Exception as e:
            print(f"Error processing command: {e}")
            return f"Error processing given command: {e}.\nCommand: {command_blurb}"

    def _parse_command(self, command: str):
        """Parse the command and extract the keyword and arguments."""
        valid_commands = [
            "SAY",
            "READ",
            "SAVE",
            "LIST",
            "DELETE",
            "FETCH",
            "EXECUTE",
            "APPEND",
            "SEARCH",
            "CLEAR_MEMORY",
            "MEMORY",
        ]
        for keyword in valid_commands:
            if command.startswith(f"[{keyword}:"):
                arg1, arg2 = self._extract_arguments(command, keyword)
                return keyword, arg1, arg2
        raise ValueError("Invalid command. Please use one of the supported commands.")

    # === Utility Methods ===

    def _extract_arguments(self, command, keyword):
        arg1 = None
        arg2 = None
        if command.startswith(f"[{keyword}:"):
            arg1 = self._extract_argument(command, keyword)
            if ":" in arg1:
                arg1, arg2 = self._extract_two_arguments(command, keyword)
        return arg1, arg2

    def _extract_argument(self, command, keyword):
        start = command.find(f"{keyword}:") + len(f"{keyword}:") + 1
        end = command.rfind('"')
        if start == -1 or end == -1 or start >= end:
            raise ValueError(f"Invalid command format for keyword '{keyword}'")
        return command[start:end]

    def _extract_two_arguments(self, command, keyword):
        args = self._extract_argument(command, keyword)
        args = args.split('":"')
        return args[0].strip(), args[1].strip()

    # === Command Handlers ===

    def say_tts(self, message):
        """Use TextToSpeech to convey the message to the user."""
        message = self._extract_argument(message, "SAY")
        self.tts.say(message)
        self.tts.runAndWait()
        print(f"TextToSpeech: {message}")
        return input("You: ")

    # === Memory Management ===

    def _add_to_memory(self, speaker, message):
        self._purge_old_memory(current_comand_to_add=message)
        self.memory.append({"speaker": speaker, "message": message})

    def _clear_memory(self):
        self.memory = []
        return "Chat History Cleared."

    def _purge_old_memory(self, max_memory_size=128000, current_comand_to_add=None):
        json_memory = json.dumps(self.memory)
        mem_size = len(json_memory)
        cmd_size = len(str(current_comand_to_add))

        if mem_size + cmd_size < max_memory_size // 0.8:
            return

        print(f"Memory Size before purge: {mem_size/1024:.2f}kb")
        while mem_size + cmd_size > max_memory_size // 0.8:
            self.memory.pop(0)
            mem_size = len(json.dumps(self.memory))
        print(f"Memory Size after purge: {mem_size/1024:.2f}kb")

    # === File Operations ===

    def _read_file(self, filename):
        filepath = os.path.abspath(filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File '{filepath}' not found.")
        with open(filepath, "r", encoding="utf-8") as file:
            return file.read()

    def _save_file(self, filename, content):
        filepath = os.path.abspath(filename)
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(content)
        return f"Content saved to '{filename}'."

    def _append_to_file(self, filename, content):
        filepath = os.path.abspath(filename)
        with open(filepath, "a", encoding="utf-8") as file:
            file.write(content)
        return f"Content appended to '{filename}'."

    def _delete_file(self, filename):
        filepath = os.path.abspath(filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File '{filepath}' not found.")
        try:
            os.remove(filepath)
            return f"File '{filename}' deleted successfully."
        except Exception as e:
            return f"Error deleting file '{filename}': {e}"

    # === Directory Operations ===

    def _list_directory(self, directory):
        dirpath = os.path.abspath(directory)
        if not os.path.exists(dirpath):
            raise FileNotFoundError(f"Directory '{dirpath}' not found.")
        if not os.path.isdir(dirpath):
            raise NotADirectoryError(f"'{dirpath}' is not a directory.")
        return ", ".join(os.listdir(dirpath))

    def _search_files(self, directory, pattern):
        dirpath = os.path.abspath(directory)
        if not os.path.exists(dirpath):
            raise FileNotFoundError(f"Directory '{dirpath}' not found.")
        if not os.path.isdir(dirpath):
            raise NotADirectoryError(f"'{dirpath}' is not a directory.")
        matching_files = fnmatch.filter(os.listdir(dirpath), pattern)
        return ", ".join(matching_files)

    # === Network Operations ===

    def _fetch_url(self, url):
        response = requests.get(url=url, timeout=10)
        response.raise_for_status()
        return response.text

    def _execute_command(self, command):
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {result.stderr.strip()}")
        return result.stdout.strip()

    # === Response Generation ===

    def generate_response(self, message: str) -> str:
        """Send message to GPT and process the response."""
        if not self.memory:
            self._add_to_memory("System", self.first_message_to_api)

        if not self.local_debug and self.client:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=self.memory,
            )

            if not response.choices:
                return "No response from GPT-4o"
            first_choice = response.choices[0]
            if not first_choice.message:
                return "First choice has no message"
            first_choice_message = first_choice.message
            if not first_choice_message.content:
                return "First choice message has no content"
            r_message = first_choice_message.content
            if not r_message:
                return "First choice message content is empty"
            self._add_to_memory("user", message)
            self._add_to_memory("assistant", r_message)
            return r_message
        else:
            r_message = '[READ:"autoGPT.py"]'
            self._add_to_memory("user", message)
            self._add_to_memory("assistant", r_message)
            return r_message


# === Main ===

if __name__ == "__main__":
    auto_gpt = AutoGPT()
    user_input = input("Task: ")
    while True:  # input("You: ")
        gpt_resp = auto_gpt.generate_response(user_input)
        user_input = auto_gpt.process_command(gpt_resp)
        # print(f"AutoGPT: {user_input}")
        memory_bytes = len(str(auto_gpt.memory))
        memory_kb = memory_bytes / 1024
        memory_mb = memory_kb / 1024
        memory_string = f"{memory_mb:.2f}MB" if memory_mb > 1 else f"{memory_kb:.2f}KB"
        # print(f"Memory: {len(auto_gpt.memory)} buffer-size: {memory_string}")

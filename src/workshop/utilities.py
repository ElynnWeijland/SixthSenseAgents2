import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ThreadMessage

from terminal_colors import TerminalColors as tc


class Utilities:
    def log_msg_green(self, msg: str) -> None:
        """Print a message in green."""
        print(f"{tc.GREEN}{msg}{tc.RESET}")

    def log_msg_purple(self, msg: str) -> None:
        """Print a message in purple."""
        print(f"{tc.PURPLE}{msg}{tc.RESET}")

    def log_token_blue(self, msg: str) -> None:
        """Print a token in blue."""
        print(f"{tc.BLUE}{msg}{tc.RESET}", end="", flush=True)

    def get_file(self, project_client: AIProjectClient, file_id: str, attachment_name: str) -> None:
        """Retrieve the file and save it to the local disk."""
        self.log_msg_green(f"Getting file with ID: {file_id}")

        file_name, file_extension = os.path.splitext(
            os.path.basename(attachment_name.split(":")[-1]))
        file_name = f"{file_name}.{file_id}{file_extension}"

        env = os.getenv("ENVIRONMENT", "local")
        folder_path = Path(f"{'src/workshop/' if env == 'container' else ''}files")

        folder_path.mkdir(parents=True, exist_ok=True)

        file_path = folder_path / file_name

        # Save the file using a synchronous context manager
        with file_path.open("wb") as file:
            for chunk in project_client.agents.get_file_content(file_id):
                file.write(chunk)

        self.log_msg_green(f"File saved to {file_path}")
        # Cleanup the remote file
        project_client.agents.delete_file(file_id)

    def get_files(self, message: ThreadMessage, project_client: AIProjectClient) -> None:
        """Get the image files from the message and kickoff download."""
        if message.image_contents:
            for index, image in enumerate(message.image_contents, start=0):
                attachment_name = (
                    "unknown" if not message.file_path_annotations else message.file_path_annotations[
                        index].text
                )
                self.get_file(project_client, image.image_file.file_id, attachment_name)
        elif message.attachments:
            for index, attachment in enumerate(message.attachments, start=0):
                attachment_name = (
                    "unknown" if not message.file_path_annotations else message.file_path_annotations[
                        index].text
                )
                self.get_file(project_client, attachment.file_id, attachment_name)

    def create_vector_store(self, project_client: AIProjectClient, files: list[str], vector_name_name: str) -> None:
        """Upload a file to the project."""

        file_ids = []
        env = os.getenv("ENVIRONMENT", "local")
        prefix = "src/workshop/" if env == "container" else ""

        # Upload the files using project_client directly
        for file in files:
            file_path = Path(f"{prefix}{file}")
            self.log_msg_purple(f"Uploading file: {file_path}")
            
            try:
                # Try different approaches for file upload
                if hasattr(project_client, 'upload_file'):
                    # Direct upload via project client
                    file_info = project_client.upload_file(
                        file_path=str(file_path),
                        purpose="assistants"
                    )
                elif hasattr(project_client.agents, 'upload_file'):
                    # Upload via agents with file object
                    with open(file_path, "rb") as f:
                        file_info = project_client.agents.upload_file(
                            file=f,
                            purpose="assistants"
                        )
                else:
                    # Try with context manager
                    with project_client as client:
                        with client.agents as agents_client:
                            with open(file_path, "rb") as f:
                                file_info = agents_client.upload_file(
                                    file=f,
                                    purpose="assistants"
                                )
                
                file_ids.append(file_info.id)
                self.log_msg_purple(f"File uploaded successfully: {file_info.id}")
                
            except Exception as e:
                self.log_msg_purple(f"Error uploading file {file_path}: {e}")
                raise

        if not file_ids:
            raise ValueError("No files were successfully uploaded")

        self.log_msg_purple("Creating the vector store")

        try:
            # Create a vector store using project_client
            if hasattr(project_client, 'create_vector_store_and_poll'):
                vector_store = project_client.create_vector_store_and_poll(
                    file_ids=file_ids, 
                    name=vector_name_name
                )
            elif hasattr(project_client.agents, 'create_vector_store_and_poll'):
                vector_store = project_client.agents.create_vector_store_and_poll(
                    file_ids=file_ids, 
                    name=vector_name_name
                )
            else:
                # Try with context manager
                with project_client as client:
                    with client.agents as agents_client:
                        vector_store = agents_client.create_vector_store_and_poll(
                            file_ids=file_ids, 
                            name=vector_name_name
                        )
            
            self.log_msg_purple(f"Vector store created and files added: {vector_store.id}")
            return vector_store
            
        except Exception as e:
            self.log_msg_purple(f"Error creating vector store: {e}")
            raise

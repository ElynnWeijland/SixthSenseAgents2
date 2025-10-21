import asyncio

from utils import initialize, post_message, cleanup, project_client, tc


async def main() -> None:
    """Interactive chat workflow that uses the helper functions in utils.py."""
    # Use the project client within a context manager for the entire session
    with project_client:
        agent, thread = await initialize()

        while True:
            print("\n")
            prompt = input(f"{tc.GREEN}Enter your query (type exit to finish): {tc.RESET}")
            if prompt.lower() == "exit":
                break
            if not prompt:
                continue
            await post_message(agent=agent, thread_id=thread.id, content=prompt, thread=thread)

        await cleanup(agent, thread)


if __name__ == "__main__":
    print("Starting async program...")
    asyncio.run(main())
    print("Program finished.")


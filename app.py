import os
import requests
import streamlit as st
from openai import OpenAI

# Initialize OpenAI client (relies on OPENAI_API_KEY env var or user input in the sidebar)
client = OpenAI()


def get_gofile_server() -> str:
    resp = requests.get("https://api.gofile.io/getServer", timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "ok" or "data" not in data or "server" not in data["data"]:
        raise RuntimeError("Failed to retrieve upload server from gofile.io.")
    return data["data"]["server"]


def upload_to_gofile(file_name: str, file_bytes: bytes) -> dict:
    """
    Uploads the given file to gofile.io and returns a dictionary with:
    {
        "downloadPage": "<public page url>",
        "directLink": "<direct file url>",
        "fileId": "<id>"
    }
    """
    server = get_gofile_server()
    files = {"file": (file_name, file_bytes)}
    resp = requests.post(f"https://{server}.gofile.io/uploadFile", files=files, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "ok" or "data" not in data:
        raise RuntimeError(f"Upload failed: {data}")

    result = data["data"]
    return {
        "downloadPage": result.get("downloadPage"),
        "directLink": result.get("directLink"),
        "fileId": result.get("fileId"),
    }


def ai_confirmation_message(link: str, filename: str) -> str:
    """
    Uses OpenAI to produce a concise confirmation message including the link.
    If API key is not available or any error occurs, falls back to a simple message.
    """
    try:
        # Quick validation for presence of API key
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY not set.")

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": (
                        f"A pitch deck file named '{filename}' has been uploaded and converted "
                        f"to a public link. Produce a concise confirmation message for the user "
                        f"with the link prominently shown. Use a friendly tone.\n\nLink: {link}"
                    ),
                },
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return f"Your pitch deck is ready! Share this global link: {link}"


def main():
    st.set_page_config(page_title="Pitch Deck to Global Link", page_icon="🌐")
    st.title("Pitch Deck to Global Link")
    st.write("Upload your pitch deck and instantly get a shareable public link.")

    with st.sidebar:
        st.header("Settings")
        st.write("Optionally add your OpenAI API key to generate a friendly confirmation message.")
        api_key = st.text_input("OPENAI_API_KEY", type="password", help="Used locally in this session.")
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key

        st.markdown("---")
        st.caption("Files are uploaded to gofile.io and a public link is returned.")

    uploaded_file = st.file_uploader(
        "Upload Pitch Deck (PDF, PPTX, PPT, or any file)",
        type=None,
        accept_multiple_files=False,
        help="Your file will be uploaded to a public hosting service to generate a shareable link."
    )

    if st.button("Generate Global Link", disabled=uploaded_file is None, use_container_width=True):
        if not uploaded_file:
            st.warning("Please upload a file first.")
            return

        filename = uploaded_file.name
        st.info(f"Uploading '{filename}' to generate a shareable link...")

        try:
            with st.spinner("Uploading to gofile.io..."):
                file_bytes = uploaded_file.getvalue()
                result = upload_to_gofile(filename, file_bytes)

            link = result.get("downloadPage") or result.get("directLink")
            if not link:
                raise RuntimeError("Failed to obtain a link from the hosting service.")

            st.success("Link generated successfully!")
            st.write("Global Link:")
            st.write(link)

            # Provide a copy-friendly field
            st.text_input("Copy Link", value=link, label_visibility="collapsed")

            # Optional AI-generated confirmation
            msg = ai_confirmation_message(link, filename)
            st.write(msg)

        except Exception as e:
            st.error(f"Failed to generate link: {e}")


if __name__ == "__main__":
    main()
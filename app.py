import streamlit as st
import requests
import ast
import json
import re


# ============================================================
# N8N WEBHOOK
# ============================================================

WEBHOOK_URL = "https://jit2005.app.n8n.cloud/webhook/gemini-assistant"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Mrittika AI Assistant",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Mrittika AI Assistant")
st.markdown("Ask a question or send a message below!")


# ============================================================
# IMAGE UPLOAD
# ============================================================

with st.sidebar:
    st.header("📷 Upload Image")

    uploaded_file = st.file_uploader(
        "Choose an image...",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file:
        st.image(
            uploaded_file,
            caption="Image ready for analysis.",
            use_container_width=True
        )


# ============================================================
# CHAT HISTORY
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ============================================================
# CLEAN N8N RESPONSE
# ============================================================

def clean_n8n_response(response):

    # --------------------------------------------------------
    # Get response as text first
    # --------------------------------------------------------

    raw_text = response.text.strip()

    # --------------------------------------------------------
    # DEBUG: remove this later if needed
    # --------------------------------------------------------

    # st.write("RAW:", raw_text)

    data = None

    # --------------------------------------------------------
    # Try JSON
    # --------------------------------------------------------

    try:
        data = response.json()
    except Exception:
        data = raw_text

    # --------------------------------------------------------
    # Unwrap n8n array
    # --------------------------------------------------------

    if isinstance(data, list):

        if len(data) > 0:
            data = data[0]
        else:
            return "No response received."


    # ========================================================
    # IF RESPONSE IS A DICTIONARY
    # ========================================================

    if isinstance(data, dict):

        # ----------------------------------------------------
        # Look for output/text/etc.
        # ----------------------------------------------------

        value = (
            data.get("output")
            or data.get("text")
            or data.get("response")
            or data.get("message")
            or data.get("content")
        )

        # ----------------------------------------------------
        # Nested json
        # ----------------------------------------------------

        if value is None and isinstance(data.get("json"), dict):

            nested = data["json"]

            value = (
                nested.get("output")
                or nested.get("text")
                or nested.get("response")
                or nested.get("message")
                or nested.get("content")
            )

        if value is not None:
            data = value

        else:
            data = str(data)


    # ========================================================
    # NOW WE SHOULD HAVE THE ACTUAL TEXT
    # ========================================================

    if not isinstance(data, str):
        data = str(data)

    text = data.strip()


    # ========================================================
    # REMOVE CODE FENCES IF AI ADDED THEM
    # ========================================================

    text = re.sub(r"^```(?:json|python)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()


    # ========================================================
    # CASE 1
    #
    # {'type': 'text', 'reply': 'Hello!'}
    # ========================================================

    if "reply" in text:

        # First try Python dictionary parsing
        try:

            parsed = ast.literal_eval(text)

            if isinstance(parsed, dict):

                if "reply" in parsed:

                    return str(parsed["reply"]).strip()

        except Exception:
            pass


        # ----------------------------------------------------
        # Try JSON parsing
        # ----------------------------------------------------

        try:

            parsed = json.loads(text)

            if isinstance(parsed, dict):

                if "reply" in parsed:

                    return str(parsed["reply"]).strip()

        except Exception:
            pass


        # ----------------------------------------------------
        # Final regex extraction
        #
        # This catches badly formatted AI output
        # ----------------------------------------------------

        match = re.search(
            r"""['"]reply['"]\s*:\s*['"](.*?)['"]\s*\}?$""",
            text,
            re.DOTALL
        )

        if match:
            return match.group(1).strip()


    # ========================================================
    # FIX ESCAPED NEWLINES
    # ========================================================

    text = text.replace("\\n", "\n")

    return text


# ============================================================
# CHAT INPUT
# ============================================================

if prompt := st.chat_input("Type your message here..."):

    # --------------------------------------------------------
    # USER MESSAGE
    # --------------------------------------------------------

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)


    # --------------------------------------------------------
    # SEND TO N8N
    # --------------------------------------------------------

    with st.chat_message("assistant"):

        with st.spinner("Thinking..."):

            try:

                payload = {
                    "message": prompt,
                    "chatInput": prompt
                }


                # =================================================
                # IMAGE REQUEST
                # =================================================

                if uploaded_file is not None:

                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type
                        )
                    }

                    response = requests.post(
                        WEBHOOK_URL,
                        data=payload,
                        files=files,
                        timeout=120
                    )


                # =================================================
                # TEXT REQUEST
                # =================================================

                else:

                    response = requests.post(
                        WEBHOOK_URL,
                        json=payload,
                        timeout=120
                    )


                # =================================================
                # HANDLE RESPONSE
                # =================================================

                if response.status_code == 200:

                    reply = clean_n8n_response(response)

                else:

                    reply = (
                        f"❌ n8n returned error "
                        f"{response.status_code}\n\n"
                        f"{response.text}"
                    )


            except requests.exceptions.Timeout:

                reply = "⏱️ n8n took too long to respond."


            except requests.exceptions.ConnectionError:

                reply = (
                    "🔌 Could not connect to the n8n webhook."
                )


            except Exception as e:

                reply = f"❌ Error: {str(e)}"


        # --------------------------------------------------------
        # DISPLAY ONLY CLEAN REPLY
        # --------------------------------------------------------

        st.markdown(reply)


    # --------------------------------------------------------
    # SAVE RESPONSE
    # --------------------------------------------------------

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply
    })
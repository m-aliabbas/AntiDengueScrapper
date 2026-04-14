import os
import sys
import time
import datetime
import threading
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from neonize.client import NewClient
from neonize.events import ConnectedEv, MessageEv, PairStatusEv, LoggedOutEv
from neonize.utils import build_jid


DEFAULT_PHONE = "923171585452"
SESSION_DB = "my_bot_session.db"

# Initialize the WhatsApp client
client = NewClient(SESSION_DB)

# Global state
connection_status = {
    "connected": False,
    "message": "Not connected yet",
    "pairing_code": None,
}

startup_state = {
    "thread_started": False
}


def get_today_date_time_pakistan_time():
    """Get today's date and time in Pakistan timezone"""
    pakistan_tz = datetime.timezone(datetime.timedelta(hours=5))
    now = datetime.datetime.now(pakistan_tz)
    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")


def set_status(
    *,
    connected: Optional[bool] = None,
    message: Optional[str] = None,
    pairing_code: Optional[str] = None,
):
    if connected is not None:
        connection_status["connected"] = connected
    if message is not None:
        connection_status["message"] = message
    if pairing_code is not None:
        connection_status["pairing_code"] = pairing_code


# Pydantic models for request/response
class SendMessageRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code (e.g., 923171585452)")
    message: str = Field(..., description="Message to send")


class SendMessageResponse(BaseModel):
    status: str
    message: str
    phone_number: str


class SendImageRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code (e.g., 923171585452)")
    image_url: str = Field(..., description="URL of the image to send")
    caption: Optional[str] = Field(None, description="Optional caption for the image")


class SendAudioRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code (e.g., 923171585452)")
    audio_url: str = Field(..., description="URL of the audio file to send")


class SendDocumentRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code (e.g., 923171585452)")
    document_url: str = Field(..., description="URL of the document to send")
    caption: Optional[str] = Field(None, description="Optional caption for the document")
    filename: Optional[str] = Field(None, description="Optional filename for the document")


class ConnectionStatus(BaseModel):
    connected: bool
    message: str
    pairing_code: Optional[str] = None


class MessageInfo(BaseModel):
    from_number: Optional[str] = None
    message_text: Optional[str] = None
    timestamp: Optional[str] = None


# Event handlers
@client.event(ConnectedEv)
def on_connected(client: NewClient, _: ConnectedEv):
    print("✅ Connection Established! You are now online.")
    set_status(
        connected=True,
        message="Connected successfully",
        pairing_code=None,
    )

    try:
        groups = client.get_joined_groups()
        if groups:
            print(groups[0])

        with open("groups.txt", "w", encoding="utf-8") as f:
            for group in groups:
                f.write(f"{group}\n")

        print(f"\nFound {len(groups)} joined groups:\n")
    except Exception as e:
        print(f"⚠️ Failed to fetch joined groups: {e}")


@client.event(PairStatusEv)
def on_pair_status(client: NewClient, pair: PairStatusEv):
    if pair.ID.User:
        print(f"✅ Logged in as: {pair.ID.User}")
        set_status(
            connected=True,
            message=f"Logged in as: {pair.ID.User}",
            pairing_code=None,
        )


@client.event(LoggedOutEv)
def on_logged_out(client: NewClient, evt: LoggedOutEv):
    print(f"❌ Disconnected: {evt.Reason}")
    set_status(
        connected=False,
        message=f"Disconnected: {evt.Reason}",
        pairing_code=None,
    )


@client.event(MessageEv)
def on_message(client: NewClient, message: MessageEv):
    if not message:
        return

    print(f"📩 New message event: {message}")
    
    # Skip if message is from ourselves
    if message.Info.MessageSource.IsFromMe:
        print("⏭️ Skipping message from self")
        return
    
    # Skip if message is from a group (optional - remove this if you want group messages too)
    if message.Info.MessageSource.IsGroup:
        print("⏭️ Skipping group message")
        return
    
    sender = str(message.Info.MessageSource.Sender.User)
    print(f"📩 New message from {sender}")

    # Get the chat JID to reply to (this is the correct way to reply)
    chat_jid = message.Info.MessageSource.Chat
    print(f"💬 Chat JID: {chat_jid}")

    # Extract message text
    text = None
    try:
        # Check for regular text message
        if message.Message.conversation:
            text = message.Message.conversation
            print(f"💬 Text (conversation): {text}")
        # Check for extended text message (replies, links, etc.)
        elif message.Message.extendedTextMessage:
            text = message.Message.extendedTextMessage.text
            print(f"💬 Text (extended): {text}")
        
        # Echo back the message (simple example - customize as needed)
        if text and text.strip():
            try:
                print(f"📤 Echoing message back to sender...")
                
                # Simple echo response
                echo_response = f"Echo: {text}"
                
                # Send the echo response back to the chat
                response = client.send_message(chat_jid, echo_response)
                print(f"✅ Message sent successfully! Response: {response}")
                print(f"✅ Sent to {sender}: {echo_response[:100]}...")
            except Exception as send_error:
                print(f"❌ Failed to send response: {send_error}")
                import traceback
                traceback.print_exc()
        else:
            print("⚠️ No text content found in message")
            
    except Exception as e:
        print(f"⚠️ Failed to process message: {e}")
        import traceback
        traceback.print_exc()

def connect_client_loop():
    """
    Keep Neonize connection loop running in a background thread.
    """
    try:
        client.connect()
    except Exception as e:
        print(f"❌ Error in WhatsApp connect loop: {e}")
        set_status(
            connected=False,
            message=f"Connection error: {str(e)}",
            pairing_code=None,
        )


def run_whatsapp_client():
    """
    Start the connect loop first, then request pairing code if needed.
    This avoids the 'client is nil' race seen when PairPhone is called
    before the underlying client is ready.
    """
    try:
        phone_number = os.getenv("WHATSAPP_PHONE", DEFAULT_PHONE)
        use_qr = os.getenv("USE_QR", "0") == "1"

        print(f"📞 Phone number for authentication: {phone_number}")

        # Start client connection loop first
        connect_thread = threading.Thread(target=connect_client_loop, daemon=True)
        connect_thread.start()

        # Give Neonize a moment to initialize its internal client
        time.sleep(2)

        # If already connected/logged in from existing session, no need to pair
        is_logged_in = bool(getattr(client, "is_logged_in", False))
        if connection_status["connected"] or is_logged_in:
            set_status(
                connected=True,
                message="Connected using existing session",
                pairing_code=None,
            )
            print("✅ Existing session detected. No new pairing required.")
            return

        if use_qr:
            print("📱 Using QR Code authentication (USE_QR enabled)")
            print("📱 Scan the QR code in the terminal")
            set_status(
                connected=False,
                message="Waiting for QR code scan",
                pairing_code=None,
            )
            return

        print(f"📞 Attempting pairing code authentication for: {phone_number}")
        print("💡 Tip: If you get rate limited, restart with: USE_QR=1 python main.py")

        try:
            pairing_code = client.PairPhone(
                phone_number,
                show_push_notification=True,
            )
            pairing_code = str(pairing_code)

            print(f"🔑 Your pairing code: {pairing_code}")
            print("Enter this code in WhatsApp → Linked Devices → Link with phone number")

            set_status(
                connected=False,
                message="Pairing code generated. Complete linking from WhatsApp.",
                pairing_code=pairing_code,
            )

        except Exception as pair_error:
            error_msg = str(pair_error)
            print(f"❌ Pairing error: {error_msg}")

            if "429" in error_msg or "rate" in error_msg.lower() or "overlimit" in error_msg.lower():
                print("")
                print("⚠️ Rate limit detected! Falling back to QR code authentication...")
                print("📱 Scan the QR code in the terminal")
                print("")

                set_status(
                    connected=False,
                    message="Waiting for QR code scan (pairing rate limited)",
                    pairing_code=None,
                )
            else:
                raise pair_error

    except Exception as e:
        print(f"❌ Error connecting WhatsApp client: {e}")
        set_status(
            connected=False,
            message=f"Connection error: {str(e)}",
            pairing_code=None,
        )


def start_whatsapp_background():
    if startup_state["thread_started"]:
        return

    thread = threading.Thread(target=run_whatsapp_client, daemon=True)
    thread.start()
    startup_state["thread_started"] = True
    print("🚀 WhatsApp client startup launched in background")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_whatsapp_background()
    yield


# Initialize FastAPI app
app = FastAPI(
    title="WhatsApp Bot API",
    description="FastAPI wrapper for Neonize WhatsApp Bot",
    version="1.0.0",
    lifespan=lifespan,
)


# API Endpoints
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API health check"""
    return {
        "status": "running",
        "service": "WhatsApp Bot API",
        "version": "1.0.0",
    }


@app.get("/kaithhealthcheck", tags=["Health"])
async def kaith_health_check():
    """Kaith health check endpoint"""
    return {
        "status": "ok",
        "service": "whatsapp-bot",
        "connected": connection_status["connected"],
    }


@app.get("/status", response_model=ConnectionStatus, tags=["Status"])
async def get_status():
    """Get the current connection status of the WhatsApp bot"""
    return connection_status


@app.get("/connected", tags=["Status"])
async def is_connected():
    """Check if WhatsApp is currently connected (real-time status)"""
    is_logged_in = bool(getattr(client, "is_logged_in", False))
    is_actually_connected = connection_status["connected"] and is_logged_in

    if not is_actually_connected and connection_status["connected"]:
        set_status(
            connected=False,
            message="Connection lost",
        )

    return {
        "connected": is_actually_connected,
        "timestamp": datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=5))
        ).isoformat(),
    }


@app.post("/send", response_model=SendMessageResponse, tags=["Messages"])
async def send_message(request: SendMessageRequest):
    """
    Send a text message to a WhatsApp number

    - **phone_number**: Phone number with country code (no + or spaces)
    - **message**: The message text to send
    """
    if not connection_status["connected"]:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp bot is not connected. Please wait for connection or complete pairing.",
        )

    try:
        if client.is_on_whatsapp(request.phone_number):
            print(f"✅ {request.phone_number} is on WhatsApp. Sending message...")
        else:
            print(f"⚠️ {request.phone_number} is NOT on WhatsApp. Message may fail.")

        jid = build_jid(request.phone_number)
        client.send_message(jid, request.message)

        return SendMessageResponse(
            status="success",
            message="Message sent successfully",
            phone_number=request.phone_number,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {str(e)}",
        )


@app.post("/send-group", response_model=SendMessageResponse, tags=["Messages"])
async def send_group_message(request: SendMessageRequest):
    """
    Send a message to a WhatsApp group

    - **phone_number**: Group ID (example: 120363408920420601)
    - **message**: The message text to send
    """
    if not connection_status["connected"]:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp bot is not connected. Please wait for connection or complete pairing.",
        )

    try:
        jid = build_jid(request.phone_number, server="g.us")
        client.send_message(jid, request.message)

        return SendMessageResponse(
            status="success",
            message="Group message sent successfully",
            phone_number=request.phone_number,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send group message: {str(e)}",
        )
@app.post("/send-image", response_model=SendMessageResponse, tags=["Messages"])
async def send_image(request: SendImageRequest):
    """
    Send an image to a WhatsApp number

    - **phone_number**: Phone number with country code (no + or spaces)
    - **image_url**: URL of the image to send
    - **caption**: Optional caption for the image
    """
    if not connection_status["connected"]:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp bot is not connected. Please wait for connection or complete pairing.",
        )

    try:
        jid = build_jid(request.phone_number)
        client.send_image(
            jid,
            request.image_url,
            caption=request.caption or "",
        )

        return SendMessageResponse(
            status="success",
            message="Image sent successfully",
            phone_number=request.phone_number,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send image: {str(e)}",
        )


@app.post("/send-audio", response_model=SendMessageResponse, tags=["Messages"])
async def send_audio(request: SendAudioRequest):
    """
    Send an audio file to a WhatsApp number

    - **phone_number**: Phone number with country code (no + or spaces)
    - **audio_url**: URL of the audio file to send
    """
    if not connection_status["connected"]:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp bot is not connected. Please wait for connection or complete pairing.",
        )

    try:
        jid = build_jid(request.phone_number)
        client.send_audio(
            jid,
            request.audio_url,
        )

        return SendMessageResponse(
            status="success",
            message="Audio sent successfully",
            phone_number=request.phone_number,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send audio: {str(e)}",
        )


@app.post("/send-document", response_model=SendMessageResponse, tags=["Messages"])
async def send_document(request: SendDocumentRequest):
    """
    Send a document to a WhatsApp number

    - **phone_number**: Phone number with country code (no + or spaces)
    - **document_url**: URL of the document to send
    - **caption**: Optional caption for the document
    - **filename**: Optional filename for the document
    """
    if not connection_status["connected"]:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp bot is not connected. Please wait for connection or complete pairing.",
        )

    try:
        jid = build_jid(request.phone_number)
        client.send_document(
            jid,
            request.document_url,
            caption=request.caption or "",
            filename=request.filename or "",
        )

        return SendMessageResponse(
            status="success",
            message="Document sent successfully",
            phone_number=request.phone_number,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send document: {str(e)}",
        )


@app.post("/send-bulk", tags=["Messages"])
async def send_bulk_messages(phone_numbers: list[str], message: str):
    """
    Send the same message to multiple phone numbers

    - **phone_numbers**: List of phone numbers with country codes
    - **message**: The message text to send to all numbers
    """
    if not connection_status["connected"]:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp bot is not connected. Please wait for connection or complete pairing.",
        )

    results = []
    for phone in phone_numbers:
        try:
            jid = build_jid(phone)
            client.send_message(jid, message)
            results.append(
                {
                    "phone_number": phone,
                    "status": "success",
                    "message": "Message sent",
                }
            )
        except Exception as e:
            results.append(
                {
                    "phone_number": phone,
                    "status": "error",
                    "message": str(e),
                }
            )

    return {
        "total": len(phone_numbers),
        "results": results,
    }


@app.post("/disconnect", tags=["Connection"])
async def disconnect():
    """Disconnect the WhatsApp bot"""
    try:
        set_status(
            connected=False,
            message="Disconnected by user",
            pairing_code=None,
        )
        return {"status": "success", "message": "Disconnected successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect: {str(e)}",
        )


@app.post("/restart", tags=["Connection"])
async def restart_server():
    """Restart the WhatsApp bot server"""
    try:
        set_status(message="Restarting server...")

        def do_restart():
            time.sleep(1)
            python = sys.executable
            os.execv(python, [python] + sys.argv)

        restart_thread = threading.Thread(target=do_restart, daemon=True)
        restart_thread.start()

        return {
            "status": "success",
            "message": "Server is restarting...",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart: {str(e)}",
        )


if __name__ == "__main__":
    print("🚀 Starting WhatsApp Bot API...")
    print("📱 If not authenticated, scan the QR code in the terminal")
    print("📡 Pairing code mode is enabled by default unless USE_QR=1")
    print("🔐 Pairing code will be available in terminal and via /status")
    print("📡 API will be available at http://localhost:8000")
    print("📚 API docs available at http://localhost:8000/docs")
    print(f"📞 Phone number: {os.getenv('WHATSAPP_PHONE', DEFAULT_PHONE)}")

    uvicorn.run(app, host="0.0.0.0", port=8000)
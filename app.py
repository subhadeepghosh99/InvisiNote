import streamlit as st
from PIL import Image
import numpy as np
import io
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import string

# --- AES Encryption Helper Functions ---
def encrypt_message(message, password):
    key = hashlib.sha256(password.encode()).digest()
    cipher = AES.new(key, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(message.encode(), AES.block_size))
    iv = base64.b64encode(cipher.iv).decode('utf-8')
    ct = base64.b64encode(ct_bytes).decode('utf-8')
    return f"{iv}:{ct}"

def decrypt_message(encrypted_message, password):
    try:
        key = hashlib.sha256(password.encode()).digest()
        iv, ct = encrypted_message.split(":")
        iv = base64.b64decode(iv)
        ct = base64.b64decode(ct)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt.decode('utf-8')
    except:
        return None

# --- Check if message is readable (ASCII printable) ---
def is_valid_message(message):
    return all(char in string.printable for char in message)

# --- LSB Encode Function ---
def encode_image(image, message):
    img = image.convert('RGB')
    data = np.array(img)
    flat_data = data.flatten()

    binary_message = ''.join([format(ord(char), '08b') for char in message]) + '1111111111111110'

    if len(binary_message) > len(flat_data):
        raise ValueError("Message is too long for this image.")

    for i in range(len(binary_message)):
        flat_data[i] = (flat_data[i] & ~1) | int(binary_message[i])

    encoded_data = flat_data.reshape(data.shape)
    encoded_img = Image.fromarray(encoded_data.astype('uint8'), 'RGB')
    return encoded_img

# --- LSB Decode Function ---
def decode_image(image):
    img = image.convert('RGB')
    data = np.array(img)
    flat_data = data.flatten()

    binary_data = ''
    for i in range(len(flat_data)):
        binary_data += str(flat_data[i] & 1)
        if binary_data.endswith('1111111111111110'):
            break
    else:
        return "__NO_MESSAGE__"

    binary_message = binary_data[:-16]
    message = ''
    try:
        for i in range(0, len(binary_message), 8):
            byte = binary_message[i:i+8]
            message += chr(int(byte, 2))
        return message if is_valid_message(message) else "__NO_MESSAGE__"
    except:
        return "__NO_MESSAGE__"

# --- Streamlit App ---
st.set_page_config(page_title="Image Steganography", layout="centered")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Encryptor", "Decryptor"])

st.title("🔐 InvisiNote: Steganography App")
st.markdown(" A Streamlit web app that securely hides and retrieves encrypted messages inside images using steganography and AES encryption.")

if page == "Encryptor":
    st.header("🖼️ Encrypt Message in Image")
    uploaded_image = st.file_uploader("Upload an image", type=["png", "bmp", "jpg", "jpeg"])
    secret_message = st.text_area("Enter the message to hide")
    password = st.text_input("Enter a password (AES encryption, optional)", type="password")

    if uploaded_image:
        image = Image.open(uploaded_image)
        max_chars = (np.array(image).size // 8) - 2
        st.info(f"Maximum characters this image can hold: {max_chars}")

    if st.button("Encrypt"):
        if uploaded_image and secret_message:
            image = Image.open(uploaded_image)
            max_chars = (np.array(image).size // 8) - 2
            if len(secret_message) > max_chars:
                st.error(f"Message too long! Reduce it to {max_chars} characters or less.")
            else:
                try:
                    final_message = encrypt_message(secret_message, password) if password else secret_message
                    encoded_image = encode_image(image, final_message)

                    buf = io.BytesIO()
                    encoded_image.save(buf, format='PNG')
                    byte_im = buf.getvalue()

                    st.image(encoded_image, caption="Encoded Image")
                    st.download_button("Download Encrypted Image", byte_im, file_name="encoded_image.png", mime="image/png")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Please upload an image and enter a message.")

elif page == "Decryptor":
    st.header("🕵️ Decrypt Message from Image")
    uploaded_image = st.file_uploader("Upload an encrypted image", type=["png", "bmp", "jpg", "jpeg"])
    password = st.text_input("Enter password if message is encrypted", type="password")

    if st.button("Decrypt"):
        if uploaded_image:
            try:
                image = Image.open(uploaded_image)
                message = decode_image(image)
                if message == "__NO_MESSAGE__":
                    st.warning("No hidden message found in the image.")
                elif password:
                    decrypted = decrypt_message(message, password)
                    if decrypted:
                        st.success("Decrypted Message:")
                        st.code(decrypted)
                    else:
                        st.error("Incorrect password or message is not encrypted with AES.")
                else:
                    st.success("Hidden Message:")
                    st.code(message)
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please upload an image.")

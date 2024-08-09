# AI-Chatroom
Here's an English README for your project:

---

# AI Chatroom

AI Chatroom is a real-time, AI-powered chat application built with Flask and Socket.IO. It integrates OpenAI's GPT models, including DALL-E, to provide interactive text conversation and image generation capabilities. The front-end leverages modern web technologies such as Bootstrap, Markdown-It, Highlight.js, and KaTeX to offer a seamless and visually appealing user experience.

## Features

### 1. Real-Time Chat
- **Instant Messaging**: Users can send and receive messages in real-time through a web interface, with messages transmitted instantly via Socket.IO.

### 2. AI-Powered Conversations
- **GPT Integration**: The chatroom is powered by OpenAI's GPT models. Users can interact with AI by mentioning `@ChatGPT` in their messages, triggering AI-generated responses.
- **Model Selection**: Users can choose from different AI models, such as `gpt-3.5-turbo`, depending on their conversational needs.

### 3. Image Generation
- **DALL-E Integration**: Users can select the DALL-E model to generate images based on text descriptions. The generated images are displayed directly within the chat interface.

### 4. User Management
- **Username Generation and Customization**: Each user is assigned a unique username upon connection. Users can edit their username, which is stored in `localStorage` for persistence.
- **Online User List**: A sidebar displays the list of currently online users, allowing users to see who else is active in the chatroom.

### 5. Message Handling and Storage
- **Message History**: The chat history is saved in the browser's `localStorage`, allowing users to retain their conversation history even after refreshing the page.
- **Content Filtering**: Messages are automatically filtered for banned words to ensure a safe and respectful environment.
- **Rate Limiting**: Users are prevented from sending messages too frequently to maintain order and avoid spam.

### 6. Command Support and Quick Input
- **Command Suggestions**: When users start typing a command with `/`, the system provides suggestions that can be quickly inserted into the input field.
- **Special Commands**: The chatroom supports various commands like clearing chat history, broadcasting messages to all users, and more.

### 7. Responsive Design
- **Mobile Optimization**: The application is optimized for different screen sizes. On smaller screens, the user list can be toggled via a hamburger menu for better usability.

### 8. Front-End Enhancements
- **Bootstrap Layout**: The app uses Bootstrap for responsive and visually appealing layouts, ensuring a consistent look across devices.
- **Markdown and Syntax Highlighting**: Messages support Markdown syntax and code highlighting, enabling rich text formatting and code snippets.
- **Math Rendering**: KaTeX is integrated to render mathematical formulas within the chat, making it suitable for academic discussions.


## Usage

- **Chat Interface**: Once the app is running, you can start chatting immediately by entering your messages in the input box. Use `@ChatGPT` to get AI-generated responses.
- **Image Generation**: Select the DALL-E model and type a description to generate an image.
- **Command Suggestions**: Type `/` in the input box to see available commands and quickly insert them.

## Contributing

Contributions are welcome! Feel free to submit a pull request or open an issue to improve the project.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- **OpenAI** for providing the powerful AI models.
- **Bootstrap, Markdown-It, Highlight.js, KaTeX** for enhancing the front-end experience.

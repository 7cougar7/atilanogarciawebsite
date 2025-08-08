# Personal Website

Welcome to my personal website repository! 🚀 This is where I showcase my projects, share my thoughts, and provide a glimpse into my journey as a developer. Whether you're here to explore my code, learn more about my skills, or simply get to know me better, I'm thrilled to have you!

## About Me

I'm Atilano Garcia (Though I go by Tilo), a passionate developer with a love for website design and making solutions that serve those who use it. This space serves as a digital playground where I experiment with ideas, contribute to open source, and document my learnings.

Feel free to browse around, check out my projects, and don't hesitate to reach out if you have any questions or collaboration ideas. Thanks for stopping by!

## Features

- **Project Showcase:** Explore my latest and greatest projects.
- **Resume and LinkedIn:** Learn about my skills, experience, and achievements.
- **Unified Authentication:** Secure passkey and magic link authentication system.
- **Personal AI:** Protected area accessible only with passkey authentication.

## Authentication System

This website features a modern, unified authentication system that supports both passkey (WebAuthn) and magic link authentication:

### Authentication Flow

1. **Unified Login Page** (`/login/`): Single entry point for all authentication
   - Enter your username to begin authentication
   - Users with passkeys will be prompted for passkey authentication
   - Users without passkeys will receive a magic link via email

2. **Passkey Authentication**:
   - Secure, passwordless authentication using WebAuthn/FIDO2
   - Uses device biometrics (Face ID, Touch ID, Windows Hello) or security keys
   - Register passkeys at `/passkeys-register/` (requires initial login)

3. **Magic Link Authentication**:
   - Email-based authentication for users without passkeys
   - Secure token-based links that expire after use
   - Automatically redirects to passkey registration after login

### Protected Areas

- **Personal AI** (`/personal-ai/`): Requires passkey authentication
  - Automatically redirects unauthenticated users to login
  - Preserves intended destination after authentication

### Key URLs

- `/login/` - Unified login page (replaces old separate login/register pages)
- `/passkeys-register/` - Passkey registration (requires login)
- `/personal-ai/` - Protected personal AI area (requires passkey)
- `/logout/` - Logout (clears all session data)

### Security Features

- CSRF protection on all authentication endpoints
- Session-based passkey authentication tracking
- Secure redirect handling to prevent open redirects
- Proper session cleanup on logout

## Getting Started

To view my website locally or contribute, follow the steps below:

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/7cougar7/atilanogarciawebsite.git
   ```

2. **Navigate to the Project Directory:**
   ```bash
   cd atilanogarciawebsite
   ```
3. **Create Environment File**
   ```bash
   touch .env; echo 'SECRET_KEY="<secret_key>"\nDEBUG="True"' > .env
   ```
4. **Run the Web Application Locally:**
     ```bash
     source ./run_local_server.sh
     ```
     This will create a virtual environment for the website, install all necessary dependencies and pre-commit hooks, and start the server locally at https://localhost:8000/

5. **Explore and Contribute:**
   Feel free to explore the code, make changes, and submit pull requests. I welcome contributions and feedback!

## Contact

- **Email:** tilogarcia1@gmail.com
- **LinkedIn:** [Atilano (Tilo) Garcia](https://www.atilanogarcia.com/linkedin)

Your curiosity is valued. Excited about our future connection for more shared learning experiences! ✨

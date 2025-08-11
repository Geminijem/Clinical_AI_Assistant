import streamlit as st

# Your existing functions like create_user(), authenticate() go here

def show_login():
    st.title("Clinical AI Assistant Login or Signup")
    option = st.selectbox("Choose an option", ["Sign In", "Sign Up", "Continue as Guest"])
    
    if option == "Sign Up":
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Create Account"):
            if not email or not password:
                st.error("Email and password are required")
                return
            uid = create_user(email, password)
            if uid:
                st.success("Account created! Please sign in.")
            else:
                st.error("Email already exists or invalid.")
    
    elif option == "Sign In":
        email = st.text_input("Email", key="signin_email")
        password = st.text_input("Password", type="password", key="signin_password")
        if st.button("Sign In"):
            if not email or not password:
                st.error("Please enter both email and password")
                return
            auth = authenticate(email, password)  # should return dict like {'id': uid, 'verified': True}
            if auth:
                st.session_state.user = auth  # store user dict here
                st.success("Signed in successfully")
                st.experimental_rerun()  # reload app with user signed in
                return  # important: stop further code now
            else:
                st.error("Invalid credentials.")
    
    else:  # Guest
        if st.button("Continue as Guest"):
            st.session_state.user = {"id": "guest", "verified": True}
            st.experimental_rerun()
            return

def main():
    # If user not logged in, show login page and stop
    if 'user' not in st.session_state or st.session_state.user is None:
        show_login()
        return  # don't run rest of app until signed in

    # User is logged in, get user info
    user = st.session_state.user
    user_id = user.get('id', 'guest')

    # Show main app interface here
    st.title("Welcome to Clinical AI Assistant!")
    st.write(f"Logged in as: {user_id}")
    
    # Example navigation menu placeholder
    menu = ["Home", "Quizzes", "Flashcards", "Bank Vaults", "Logout"]
    choice = st.sidebar.selectbox("Navigate", menu)
    
    if choice == "Logout":
        st.session_state.user = None
        st.experimental_rerun()
    
    elif choice == "Home":
        st.write("This is the Home page.")
    elif choice == "Quizzes":
        st.write("Here are your quizzes.")
    elif choice == "Flashcards":
        st.write("Here are your flashcards.")
    elif choice == "Bank Vaults":
        st.write("Here is your bank vault.")

if __name__ == "__main__":
    main()

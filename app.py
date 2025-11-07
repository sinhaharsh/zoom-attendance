import streamlit as st
from nodes import collect_attendance_from_bunny, get_participant_meeting_stats

st.title("Zoom Attendance Participant Search")

@st.cache_data
def load_data():
    return collect_attendance_from_bunny()

df = load_data()

query = st.text_input("Enter participant name or email to search:")

if query:
    result = get_participant_meeting_stats(df, query)
    if result["type"] == "email":
        st.subheader(f"Results for email: {result['query']}")
        st.write(f"Meetings attended: {result['meetings_attended']}")
        st.write(f"Total meetings: {result['total_meetings']}")
    elif result["type"] == "name":
        st.subheader(f"Fuzzy search results for name: {result['query']}")
        if result["matches"]:
            for match in result["matches"]:
                st.write(f"Name: {match['name']}")
                st.write(f"Email: {match['email']}")
                st.write(f"Meetings attended: {match['meetings_attended']}")
                st.write(f"Total meetings: {match['total_meetings']}")
                st.write("---")
        else:
            st.write("No close matches found.")

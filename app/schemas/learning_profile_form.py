LEARNING_PROFILE_FORM = {
    "section_1": {
        "title": "Learning Style Preferences",
        "instruction": "Rate how much you agree with the following: 1 (Strongly Disagree) → 5 (Strongly Agree)",
        "type": "rating",
        "questions": [
            {"style": "Visual", "question": "I understand better with diagrams or visual aids."},
            {"style": "Visual", "question": "Watching videos or animations helps me learn faster."},
            {"style": "ReadingWriting", "question": "I learn effectively by reading or writing about a topic."},
            {"style": "ReadingWriting", "question": "I prefer written instructions over videos or explanations."},
            {"style": "Kinesthetic", "question": "I understand best by doing hands-on activities."},
            {"style": "Kinesthetic", "question": "I enjoy solving real-world problems or doing experiments."},
            {"style": "Visual", "question": "I remember things best when I visualize them."},
            {"style": "ReadingWriting", "question": "I retain info better when I write it down."},
            {"style": "Kinesthetic", "question": "I get bored quickly in passive learning situations."}
        ]
    },
    "section_2": {
        "title": "Behavior & Preferences",
        "instruction": "Select the one that best describes you.",
        "type": "mcq",
        "questions": [
            {
                "question": "When are you most productive?",
                "options": [
                    "early_morning",
                    "late_morning",
                    "afternoon",
                    "evening"
                ]
            },
            {
                "question": "How do you usually study?",
                "options": [
                    "silence",
                    "music",
                    "cafe_noise",
                    "with_person"
                ]
            },
            {
                "question": "Your learning goal right now?",
                "options": [
                    "pass_exams",
                    "deep_understanding",
                    "job_prep",
                    "curious"
                ]
            }
        ]
    }
}

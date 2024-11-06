def generate_prompt(options):
    sort = options.get('sort', 'review')
    topic = options.get('topic', 'general topic')
    tone_example = options.get('tone_example', 'conversational tone')
    main_message = options.get('main_message', 'core message')

    # 프롬프트 생성
    prompt = (
        f"""
        I am writing a blog post where the type of post is {sort}. 
        The main topic is about {topic}. Please write it in a {tone_example} style,
        and emphasize that the key message of the post is '{main_message}'.
        """
    )
    return prompt
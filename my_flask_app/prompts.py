def generate_prompt(options):
    sort = options.get('sort', 'review')
    topic = options.get('topic', 'general topic')
    tone_example = options.get('tone_example', 'conversational tone')
    main_message = options.get('main_message', 'core message')

    # 프롬프트 생성
    prompt = (
        # f"""
        # I am writing a blog post where the type of post is {sort}. 
        # The main topic is about {topic}. Please write it in a {tone_example} style,
        # and emphasize that the key message of the post is '{main_message}'.
        # """
        f"""
        블로그 포스팅을 할 건데, 
        포스팅 종류는 {sort}이고, 게시물 주제는 {topic} 의 내용을 가져. 
        텍스트 말투는 {tone_example} 와 같은 말투로 작성해주고, 
        포스팅 작성에서 가장 중요한 키워드는 {main_message}야.
        """
    )
    return prompt
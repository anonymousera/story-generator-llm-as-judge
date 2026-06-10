# Hippocratic AI Coding Assignment
Welcome to the [Hippocratic AI](https://www.hippocraticai.com) coding assignment

## Instructions
The attached code is a simple python script skeleton. Your goal is to take any simple bedtime story request and use prompting to tell a story appropriate for ages 5 to 10.
- Incorporate a LLM judge to improve the quality of the story
- Provide a block diagram of the system you create that illustrates the flow of the prompts and the interaction between judge, storyteller, user, and any other components you add
- Do not change the openAI model that is being used. 
- Please use your own openAI key, but do not include it in your final submission.
- Otherwise, you may change any code you like or add any files

---

## Rules
- This assignment is open-ended
- You may use any resources you like with the following restrictions
   - They must be resources that would be available to you if you worked here (so no other humans, no closed AIs, no unlicensed code, etc.)
   - Allowed resources include but not limited to Stack overflow, random blogs, chatGPT et al
   - You have to be able to explain how the code works, even if chatGPT wrote it
- DO NOT PUSH THE API KEY TO GITHUB. OpenAI will automatically delete it

---

## What does "tell a story" mean?
It should be appropriate for ages 5-10. Other than that it's up to you. Here are some ideas to help get the brain-juices flowing!
- Use story arcs to tell better stories
- Allow the user to provide feedback or request changes
- Categorize the request and use a tailored generation strategy for each category

---

## How will I be evaluated
Good question. We want to know the following:
- The efficacy of the system you design to create a good story
- Are you comfortable using and writing a python script
- What kinds of prompting strategies and agent design strategies do you use
- Are the stories your tool creates good?
- Can you understand and deconstruct a problem
- Can you operate in an open-ended environment
- Can you surprise us

---

## Other FAQs
- How long should I spend on this? 
No more than 2-3 hours
- Can I change what the input is? 
Sure
- How long should the story be?
You decide


## My Notes:
- The stories should be appropriate for ages 5 to 10.: Compulsory
- The stories should use simple language and grammar, and not use any complex words or grammar.
- The stories should not have sentences that are too long, i.e. should be less than 20 words.
- The stories should not have any violence or scary content.: Compulsory
- The stories should not have any bad words or inappropriate content.: Compulsory
- The stories should not have any political or religious content. This is a children's story, so it should not be too mature.: Compulsory
- The stories should be fun and engaging, and should be able to hold the attention of a 5 to 10 year old.
- The stories should be able to be read aloud by a 5 to 10 year old.
- The stories should not have any controversial content.: Compulsory
- The stories should be appropriate for any children of any race, gender, or ethnicity.: Compulsory   
- The stories should be appropriate for any children of any religious or spiritual background.: Compulsory  
- The stories should be appropriate for any children of any educational background.: Compulsory
- The stories should be appropriate for any children of any socioeconomic background.: Compulsory
- The stories should be appropriate for any children of any cultural background.: Compulsory
- The stories should be appropriate for any children of any language background, though the story should be in English.
- The stories should be appropriate for any children of any disability background.: Compulsory
- The stories should be appropriate for any children of any sexual orientation background.: Compulsory
- The stories should be appropriate for any children of any gender identity background.: Compulsory
- The stories should be appropriate for any children of any region of the world.

# Judge:
- might need to use different model for judge and storyteller.

The judge is used to score the storyteller's story on a provided scale, to assess a property of the text (fluency, toxicity, coherence, persuasiveness, etc).
The judge is also used to compare a pair model outputs to pick the best text with respect to a given property.
The judge is also used to compute the similarity between a model output and a reference.

# Storyteller:
The storyteller is used to generate a story based on the user's request.
The storyteller is also used to generate a story based on the judge's feedback.
The storyteller is also used to generate a story based on the user's request.

# User:
The user is used to request a story from the storyteller.

# Prompt design guidelines
Provide a clear description of the task at hand:

Your task is to do X.
You will be provided with Y.
Provide clear instructions on the evaluation criteria, including a detailed scoring system if needed:

You should evaluate property Z on a scale of 1 - 5, where 1 means …
You should evaluate if property Z is present in the sample Y. Property Z is present if …
Provide some additional “reasoning” evaluation steps:

To judge this task, you must first make sure to read sample Y carefully to identify …, then …
Specify the desired output format (adding fields will help consistency)

Your answer should be provided in JSON, with the following format {“Score”: Your score, “Reasoning”: The reasoning which led you to this score}

# To remember when doing model as judge
Pairwise comparison correlates better with human preference than scoring, and is more robust generally.

If you really want a score, use an integer scale make sure you provide a detailed explanation for what each score represents, or an additive prompt (provide 1 point for this characteristic of the answer, 1 additional point if … etc)

Using one prompt per capability to score tends to give better and more robust results

# You can also improve accuracy using the following, possibly more costly, techniques:

Few shot examples: like in many other tasks, if you provide examples it can help its reasoning. However, this adds to your context length.
Reference: you can also enhance your prompt with a reference if present, which increases accuracy
CoT: improves accuracy for older gen models, if you ask the model to output its chain of thought before the score (also observed here)
Multiturn analysis: can improve factual error detection
Using a jury (many judges, where you pick an aggregate of the answers): gives better results than using a single model. It can be made considerably less costly by leveraging many smaller models instead of one big expensive model. You can also experiment with using one model with variations on temperature
Surprisingly, the community has found that adding stakes to the prompts (answer correctly and you'll get a kitten) can increase correctness. Your mileage may vary on this one, adapt to your needs.

# Building Agent Techniques::
- Routing. 
- Parallel execution: voting for multiple perspectives.
- Evaluator-optimizer workflow 



##
Q) Before submitting the assignment, describe here in a few sentences what you would have built next if you spent 2 more hours on this project:
Ans)
1)  I'll run experiments to manually evaluate performace of the system, primarily to understand if it is too complex, or without so many constraints it could have performed similar or better. 
Right now I'm implementing based on industry best practices, my own innovation to the system diagram, and my own context-specific knowledge. 
2) Either th above, or  another experiment I would have done is optimizing the 4 metrics I've used in the system and see if  it can perform better. . 

# Other few ideaas worth exploring: 

- Training your own LLM-as-judge. You can also make the choice to train or fine-tune your own LLM-as-judge. 
- If you are working on critical tasks (medical domain for example), make sure to use methodologies transferred from the humanities, and 
1) compute inter-annotator agreement metrics to make sure your evaluators are as unbiased as possible, 
2) Use proper survey design methodology when creating your scoring grid to mitigate bias.
- Quality over quantity for baseline
You don’t need many baseline examples (50 can suffice), but they must be:
Representative: Cover the full range of your task
Discriminative: Include edge cases and challenging examples
High quality: Use the best reference data you can obtain
- Improving the metrics to judge the judge's evaluation of the storyteller's story.
- Mitigating well known biases of LLM as judges
We discussed in this section’s intro a number of LLM judges biases. Let’s see how you should try to mitigate them.

Lack of internal consistency: ➡️ You can mitigate this by doing self-consistency prompting of your judge, prompting it multiple times and keeping the majority output

Self-preference: ➡️ You can mitigate this by using a jury

Blindness to input perturbation: ➡️ asking the model to explain its reasoning before providing a score ➡️ or providing a coherent grading scale in the prompt.

Position-bias: ➡️ switching answer positions randomly ➡️ computing the log-probabilities of all possible choices to get a normalized answer

Verbosity-bias (or length-bias): ➡️ You can mitigate this by accounting for the answer difference in length

Format bias: ➡️ You can mitigate this by paying attention to the training prompt format (if the model was instruction tuned) and ensuring you follow it.
- Reward models?
- multiple judges and different models, not same model for story-teller and judge(s).  

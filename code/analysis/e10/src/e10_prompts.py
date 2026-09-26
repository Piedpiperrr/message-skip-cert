"""E10 frozen prompt construction.  Written before any GSM8K model output exists and hashed with
the preregistration receipt.

Derivation from the frozen Text-path protocol (P2_10 protocol_min.build_prompt /
legacy_methods.BACKGROUND_PROMPT), recorded exactly:

* Helper prompt = the frozen BACKGROUND_PROMPT with the question body substituted.  In the frozen
  multiple-choice path the body is format_openbook(example, use_template=False), i.e.
  `question + "\n\nChoices:\n" + choices`.  PREREG_E10 says the GSM8K question is substituted for
  the multiple-choice question "and with the option list removed", so the body is the bare GSM8K
  question.  Nothing else changes.

* Receiver prompt = the frozen build_prompt(..., use_cot=True) template, which is the variant of
  the frozen builder that asks for a worked solution (PREREG_E10 raises the receiver cap to 320
  tokens precisely "because a short-answer solution does not fit in 64").  Two edits, both forced
  by PREREG_E10: the "Choices:" block is removed with the option list, and the final-answer
  instruction is replaced by the exact string PREREG_E10 prescribes.  The bullet
  "- Carefully read the question and all options." loses its option clause because there are no
  options.  No other change.  See DEVIATIONS.md.

* Receiver-with-message prompt = the frozen three-turn Text structure of
  legacy_methods.T2TReceiverBundle.consume: user=BACKGROUND_PROMPT(body), assistant=helper message,
  user=receiver prompt.  Unchanged apart from the receiver prompt above.
"""

# verbatim from P2_10 legacy_methods.BACKGROUND_PROMPT
BACKGROUND_PROMPT = ("In one clear sentence, describe the most essential background knowledge "
                     "needed to answer the question:\n\n{question}\n\n"
                     "Do NOT directly solve or give answer to the question.")

# The frozen use_cot=True template of P2_10 protocol_min.build_prompt, with the option list
# removed and the final-answer instruction replaced as PREREG_E10 prescribes.  The trailing
# whitespace on the second line is present in the frozen template and is kept byte for byte.
RECEIVER_TEMPLATE = """Accurately answer the following question:
                   
{{question}}

Instructions:
- Carefully read the question.
- Let's think step by step and explain your reasoning briefly.
- End your response with the exact string "The answer is <number>.\""""

ANSWER_INSTRUCTION = 'The answer is <number>.'


def helper_body(question):
    """The question body the helper sees (option list removed => the bare GSM8K question)."""
    return str(question)


def helper_prompt(question):
    return BACKGROUND_PROMPT.format(question=helper_body(question))


def receiver_prompt(question):
    return RECEIVER_TEMPLATE.replace('{{question}}', str(question))


def receiver_only_messages(question):
    return [{'role': 'user', 'content': receiver_prompt(question)}]


def receiver_with_message_messages(question, helper_message):
    return [{'role': 'user', 'content': helper_prompt(question)},
            {'role': 'assistant', 'content': helper_message},
            {'role': 'user', 'content': receiver_prompt(question)}]

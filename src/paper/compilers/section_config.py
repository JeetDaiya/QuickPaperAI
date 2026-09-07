from collections import OrderedDict
from src.paper.models import QuestionTypes

SECTION_CONFIG = OrderedDict({
    QuestionTypes.MCQ: "Multiple Choice Questions",
    QuestionTypes.TRUE_FALSE: "True or False",
    QuestionTypes.FILL_IN_THE_BLANK: "Fill in the Blanks",
    QuestionTypes.ONE_WORD_ANS: "One Word Answer",
    QuestionTypes.MATCH_THE_COLUMN: "Match the Following",
    QuestionTypes.TWO_MARK_ANS: "Short Answer Questions (2 Marks)",
    QuestionTypes.THREE_MARK_ANS: "Short Answer Questions (3 Marks)",
    QuestionTypes.FOUR_MARK_ANS: "Long Answer Questions (4 Marks)",
})

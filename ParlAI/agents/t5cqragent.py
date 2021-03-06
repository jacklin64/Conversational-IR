from parlai.core.agents import register_agent, Agent
from parlai.core.torch_agent import History
from pyserini.search import SimpleSearcher
from transformers import T5Tokenizer, T5ForConditionalGeneration
import json


class T5CQR(object):
    def __init__(self, pretrained_ckpt):
        try:
            self.model = T5ForConditionalGeneration.from_pretrained(pretrained_ckpt)
            self.tokenizer = T5Tokenizer.from_pretrained(pretrained_ckpt)
        except ValueError as e:
            print(str(e))
            return None

        self.history = []
        print(f'Initializing {pretrained_ckpt}...')
    
    def rewrite(self, query):
        self.history += [query]
        source_text  = ' '.join(self.history)
        input_ids    = self.tokenizer(source_text, return_tensors="pt", add_special_tokens=True).input_ids
        output_ids   = self.model.generate(input_ids)
        rewrite_text = self.tokenizer.decode(output_ids[0, 0:], clean_up_tokenization_spaces=True, skip_special_tokens=True)
        
        return rewrite_text

    def reset_history(self):
        self.history = []


@register_agent("t5cqrbm25ranker")
class T5CQRBM25Agent(Agent):
    @classmethod
    def add_cmdline_args(cls, parser, partial_opt):
        parser.add_argument('--name', type=str, default='T5CQR-BM25', help="The agent's name.")
        parser.add_argument('--from_pretrained', type=str, default='castorini/t5-base-canard', help="HGF T5 CQR checkpoint.")
        parser.add_argument('--from_prebuilt', type=str, default='cast2019', help="Pyserini prebuilt index.")
        parser.add_argument('--episode_done', type=str, default='[END]', help="End signal for interactive mode")
        return parser
        
    def __init__(self, opt, shared=None):
        # similar to the teacher, we have the Opt and the shared memory objects!
        super().__init__(opt, shared)
        self.id = 'T5CQRBM25Ranker'
        self.name = opt['name']
        self.episode_done = opt['episode_done']
        self.cqr  = T5CQR(opt['from_pretrained'])
        self.searcher = SimpleSearcher.from_prebuilt_index(opt['from_prebuilt'])

    def observe(self, observation):
        # Gather the last word from the other user's input
        self.query = observation.get('text', '')
        if observation.get('episode_done') or self.query == self.episode_done:
            print('Reset History')
            self.cqr.reset_history()
    
    def act(self):
        # Always return a string like this.
        if self.query == self.episode_done:
            
            return {
                'id': self.id,
                'text': 'Session finished'}

        rewrite_text = self.cqr.rewrite(self.query)
        hits = self.searcher.search(rewrite_text, 1)

        return {
            'id': self.id,
            'text': self.searcher.doc(hits[0].docid).raw(),
        }

if __name__ == '__main__':
    from parlai.scripts.display_data import DisplayData
    from parlai.scripts.display_model import DisplayModel
    from parlai.core.teachers import register_teacher, DialogTeacher

    @register_teacher("my_teacher")
    class MyTeacher(DialogTeacher):
        def __init__(self, opt, shared=None):
            # opt is the command line arguments.
            
            # What is this shared thing?
            # We make many copies of a teacher, one-per-batchsize. Shared lets us store 
            
            # We just need to set the "datafile".  This is boilerplate, but differs in many teachers.
            # The "datafile" is the filename where we will load the data from. In this case, we'll set it to
            # the fold name (train/valid/test) + ".txt"
            opt['datafile'] = opt['datatype'].split(':')[0] + ".txt"
            self.id = 'teacher'
            super().__init__(opt, shared)
        
        def setup_data(self, datafile):
            # filename tells us where to load from.
            # We'll just use some hardcoded data, but show how you could read the filename here:
            print(f" ~~ Loading from {datafile} ~~ ")
            
            # setup_data should yield tuples of ((text, label), new_episode)
            # That is ((str, str), bool)
            
            # first episode
            # notice how we have call, response, and then True? The True indicates this is a first message
            # in a conversation
            yield ('Frank Zappa Disbandment What group disbanded?', 'What group disbanded?'), True
            # Next we have the second turn. This time, the last element is False, indicating we're still going
            yield ('Zappa and the Mothers of Invention When did they disband?', 'When did Zappa and the Mothers of Invention disband?'), False
            yield ("In late 1969, Zappa broke up the band. What kind of music did they play?", 'What kind of music did Zappa and the Mothers of Invention play?'), False
    
    #DisplayData.main(task="my_teacher")

    #DisplayModel.main(task='my_teacher', model='t5cqrbm25ranker')

    from parlai.scripts.interactive import Interactive
    Interactive.main(model='t5cqrbm25ranker')


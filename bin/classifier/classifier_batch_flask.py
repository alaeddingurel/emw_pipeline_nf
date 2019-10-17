import os
from nltk import sent_tokenize
import numpy
from pathlib import Path
import torch
from pytorch_pretrained_bert.tokenization import BertTokenizer
from pytorch_pretrained_bert.modeling import BertForSequenceClassification
from sklearn.externals import joblib

# Import the framework
from flask import Flask, g
from flask_restful import Resource, Api, reqparse
# Create an instance of Flask
app = Flask(__name__)

# Create the API
api = Api(app)

PYTORCH_PRETRAINED_BERT_CACHE = Path(os.getenv('PYTORCH_PRETRAINED_BERT_CACHE',
                                               Path.home() / '.pytorch_pretrained_bert'))
HOME=os.getenv("HOME")

@app.route("/")
def index():
    # Open the README file
    #with open(os.path.dirname(app.root_path) + '/README.md', 'r') as markdown_file:
    # Read the content of the file
    #content = str("\n ".join(main(file)))

    # Convert to HTML
    if classifer is not None :
        # return markdown.markdown("classifier is loaded")
        return "<html><body><p>classifier is loaded</p></body></html>"
    else :
        return "<html><body><p>classifier is not loaded</p></body></html>"
        # return markdown.markdown("classifier is not loaded")

# def predict (input):
#    return  classifer.predict([input])[0]

def convert_text_to_features(text, label_list, max_seq_length, tokenizer):
    label_map = {}
    for (i, label) in enumerate(label_list):
        label_map[label] = i

    tokens_a = tokenizer.tokenize(text)
    if len(tokens_a) > max_seq_length - 2:
        tokens_a = tokens_a[0:(max_seq_length - 2)]

    tokens = []
    segment_ids = []
    tokens.append("[CLS]")
    segment_ids.append(0)

    for token in tokens_a:
        tokens.append(token)
        segment_ids.append(0)

    tokens.append("[SEP]")
    segment_ids.append(0)

    input_ids = tokenizer.convert_tokens_to_ids(tokens)
    input_mask = [1] * len(input_ids)

    while len(input_ids) < max_seq_length:
        input_ids.append(0)
        input_mask.append(0)
        segment_ids.append(0)

    assert len(input_ids) == max_seq_length
    assert len(input_mask) == max_seq_length
    assert len(segment_ids) == max_seq_length

    return input_ids, input_mask, segment_ids

def predict(texts):

    # svm_predicted = svm_model.predict_proba(text)
    # svm_predicted = [0 if i[0] >= 0.95 else 1 for i in svm_predicted]

    # if svm_predicted[0] == 1:
    #     input_ids, input_mask, segment_ids = convert_text_to_features(text, label_list, max_seq_length, tokenizer)
    #     input_ids = torch.tensor(input_ids, dtype=torch.long).unsqueeze(0).to(device)
    #     input_mask = torch.tensor(input_mask, dtype=torch.long).unsqueeze(0).to(device)
    #     segment_ids = torch.tensor(segment_ids, dtype=torch.long).unsqueeze(0).to(device)

    #     logits = model(input_ids, segment_ids, input_mask)
    #     logits = logits.detach().cpu().numpy()
    #     label = numpy.argmax(logits, axis=1)
    #     label = label[0]

    # else:
    #     label = 0

    all_input_ids = list()
    all_input_mask = list()
    all_segment_ids = list()
    for text in texts:
        input_ids, input_mask, segment_ids = convert_text_to_features(text, label_list, max_seq_length, tokenizer)
        input_ids = torch.tensor(input_ids, dtype=torch.long).unsqueeze(0)
        input_mask = torch.tensor(input_mask, dtype=torch.long).unsqueeze(0)
        segment_ids = torch.tensor(segment_ids, dtype=torch.long).unsqueeze(0)
        all_input_ids.append(input_ids)
        all_input_mask.append(input_mask)
        all_segment_ids.append(segment_ids)

    all_input_ids = torch.cat(all_input_ids, dim=0).to(device)
    all_input_mask = torch.cat(all_input_mask, dim=0).to(device)
    all_segment_ids = torch.cat(all_segment_ids, dim=0).to(device)
    logits = model(all_input_ids, all_segment_ids, all_input_mask)
    logits = logits.detach().cpu().numpy()
    label = numpy.argmax(logits, axis=1).tolist()

    return label

class queryList(Resource):
    def post(self):
        parser = reqparse.RequestParser()

        parser.add_argument('texts', required=False, type=str, action='append', default=[])
        parser.add_argument('outputs', required=False)
        parser.add_argument('event_sentences', required=False)
        # Parse the arguments into an object
        args = parser.parse_args()
        args["outputs"] = predict(args['texts'])
        args["event_sentences"] = list()
        for i,output in enumerate(args["outputs"]):
            if output == 1:
                args["event_sentences"].append(sent_tokenize(args['texts'][i]))

        return args, 201

label_list = ["0", "1"]
max_seq_length = 256

bert_model = HOME+"/.pytorch_pretrained_bert/bert-base-uncased.tar.gz"
bert_vocab = HOME+"/.pytorch_pretrained_bert/bert-base-uncased-vocab.txt"
model_path = HOME+"/.pytorch_pretrained_bert/doc_model.pt"
# svm_model = "/scratch/users/omutlu/.pytorch_pretrained_bert/svm_model.pkl"

num_labels = len(label_list)
# device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
device = torch.device("cuda:0")
# svm_model = joblib.load(svm_model)

tokenizer = BertTokenizer.from_pretrained(bert_vocab)
model = BertForSequenceClassification.from_pretrained(bert_model, PYTORCH_PRETRAINED_BERT_CACHE, num_labels=num_labels)
if torch.cuda.is_available():
    model.load_state_dict(torch.load(model_path))
else:
    model.load_state_dict(torch.load(model_path, map_location='cpu'))

model = torch.nn.DataParallel(model, device_ids=[0,1,2,3,4,5], output_device=device, dim=0)
model.to(device)

api.add_resource(queryList, '/queries')
app.run(host='0.0.0.0', port=5000, debug=True)

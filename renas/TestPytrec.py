import pytrec_eval
import json

qrel = {
    'q1': {
        'd1': 0,
        'd2': 1,
        'd3': 0,
    },
    'q2': {
        'd2': 1,
        'd3': 1,
    },
}

run = {
    'q1': {
        'd1': 1.0,
        'd2': 0.0,
        'd3': 1.5,
    },
    'q2': {
        'd1': 1,
        'd2': 2,
        'd3': 0.5,
    }
}

evaluator = pytrec_eval.RelevanceEvaluator(
    qrel, {'map', 'ndcg', 'recall', 'recip_rank', 'P'})
print(pytrec_eval.supported_measures)
print(json.dumps(evaluator.evaluate(run), indent=1))
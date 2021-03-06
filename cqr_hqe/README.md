# HQE for Conversational Query Reformulation

## Data Preparation

The input query file ([train](https://github.com/daltonj/treccastweb/blob/master/2019/data/training/train_topics_v1.0.json) and [evaluation](https://github.com/daltonj/treccastweb/blob/master/2019/data/evaluation/evaluation_topics_v1.0.json)) for HQE is the json format.

## Run HQE using Anserini

```shell=bash
python ./retrieve_with_hqe.py \
      --hits 1000 \
      --index $index \
      --qid_queries $input_query \
      --output ./output/hqe_bm25 \
```

After running the above script, you can get two files, hqe_bm25.tsv and hqe_bm25.doc.tsv. The first one is the retrieval results using BM25 and the second one can be directly used to generate tfrecord file for [BERT passage re-ranking](https://github.com/nyu-dl/dl4marco-bert).

## Evaluate HQE

We first remove the query-document pair with zero relevence score in [train_topics_mod.qrel](https://github.com/daltonj/treccastweb/blob/master/2019/data/training/train_topics_mod.qrel) and evaluation_topics_mod.qrel (if available) as answer files.

```shell=bash
awk -F " " '{if ($4>0) print($1 " " $2 " " $3 " " $4)}' train_topics_mod.qrel > ./answer_file
```

Finally, we convert hqe_bm25.tsv to trec file and use trec tool to evaluate the resuls in terms of Recall@1000, mAP and NDCG@1,3.

```shell=bash
python $path_for_anserini/tools/scripts/msmarco/convert_msmarco_to_trec_run.py \
      --input ./output/hqe_bm25.tsv \
      --output ./output/hqe_bm25.trec

$path_for_anserini/tools/eval/trec_eval.9.0.4/trec_eval \
      -c -mrecall.1000 -mmap -mndcg_cut.1,3 \
      ./answer_file \
      ./output/hqe_bm25.trec
```

## Evaluation results

The results of eval set is better than the number we reported in our paper due to the removal of Washington Post in our Corpus here.

| Results     | Train  |  Eval  |
| ----------- | :----: | :----: |
| mAP         | 0.1492 | 0.2114 |
| Recall@1000 | 0.8698 | 0.7297 |
| NDCG@1      | 0.0952 | 0.2611 |
| NDCG@3      | 0.1205 | 0.2586 |

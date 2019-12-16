# import json
# import torch
# import torch.utils.data as data
# import unicodedata
# import string
# import re
# import random
# import time
# import math
# import torch
# import torch.nn as nn
# import torch.nn.functional as F
# from utils.config import *
# import ast
# from collections import Counter
# from collections import OrderedDict
# from embeddings import GloveEmbedding, KazumaCharEmbedding
# from tqdm import tqdm
# import os
# import pickle
# from random import shuffle
# from pytorch_pretrained_bert import BertTokenizer
#
# tokenizer = BertTokenizer.from_pretrained('bert-large-uncased')
#
# from .fix_label import *
#
# EXPERIMENT_DOMAINS = ["hotel", "train", "restaurant", "attraction", "taxi"]
# COMBINED_DOMAINS = []
#
#
# class Lang:
#     def __init__(self):
#         self.word2index = {}
#         self.index2word = {PAD_token: "PAD", SOS_token: "SOS", EOS_token: "EOS", UNK_token: 'UNK'}
#         self.n_words = len(self.index2word)  # Count default tokens
#         self.word2index = dict([(v, k) for k, v in self.index2word.items()])
#
#     def index_words(self, sent, type):
#         if type == 'utter':
#             for word in sent:
#                 self.index_word(word)
#         elif type == 'slot':
#             for slot in sent:
#                 d, s = slot.split("-")
#                 self.index_word(d)
#                 for ss in s.split(" "):
#                     self.index_word(ss)
#         elif type == 'belief':
#             for slot, value in sent.items():
#                 d, s = slot.split("-")
#                 self.index_word(d)
#                 for ss in s.split(" "):
#                     self.index_word(ss)
#                 for v in value.split(" "):
#                     self.index_word(v)
#
#     def index_word(self, word):
#         if word not in self.word2index:
#             token = []
#             token.append(word)
#             self.word2index[word] = tokenizer.convert_tokens_to_ids(token)[0]
#             idx = self.word2index[word]
#             self.index2word[idx] = word
#             self.n_words += 1
#
#
# class Dataset(data.Dataset):
#     """Custom data.Dataset compatible with data.DataLoader."""
#
#     def __init__(self, data_info, src_word2id, trg_word2id, sequicity, mem_word2id):
#         """Reads source and target sequences from txt files."""
#         self.ID = data_info['ID']
#         self.turn_domain = data_info['turn_domain']
#         self.turn_id = data_info['turn_id']
#         self.dialog_history = data_info['dialog_history']
#         self.turn_belief = data_info['turn_belief']
#         self.gating_label = data_info['gating_label']
#         self.turn_uttr = data_info['turn_uttr']
#         self.generate_y = data_info["generate_y"]
#         self.sequicity = sequicity
#         self.num_total_seqs = len(self.dialog_history)
#         self.src_word2id = src_word2id
#         self.trg_word2id = trg_word2id
#         self.mem_word2id = mem_word2id
#
#     def __getitem__(self, index):
#         """Returns one data pair (source and target)."""
#         ID = self.ID[index]
#         turn_id = self.turn_id[index]
#         turn_belief = self.turn_belief[index]
#         gating_label = self.gating_label[index]
#         turn_uttr = self.turn_uttr[index]
#         turn_domain = self.preprocess_domain(self.turn_domain[index])
#         generate_y = self.generate_y[index]
#         generate_y = self.preprocess_slot(generate_y, self.trg_word2id)
#         context = self.dialog_history[index]
#         context = self.preprocess(context, self.src_word2id)
#         context_plain = self.dialog_history[index]
#
#         item_info = {
#             "ID": ID,
#             "turn_id": turn_id,
#             "turn_belief": turn_belief,
#             "gating_label": gating_label,
#             "context": context,
#             "context_plain": context_plain,
#             "turn_uttr_plain": turn_uttr,
#             "turn_domain": turn_domain,
#             "generate_y": generate_y,
#         }
#         return item_info
#
#     def __len__(self):
#         return self.num_total_seqs
#
#     def preprocess(self, sequence, word2idx):
#         """Converts words to ids."""
#         story = [word2idx[word] if word in word2idx else UNK_token for word in sequence]
#         story = torch.Tensor(story)
#         return story
#
#     def preprocess_slot(self, sequence, word2idx):
#         """Converts words to ids."""
#         story = []
#         for value in sequence:
#             v = [word2idx[word] if word in word2idx else UNK_token for word in value.split()] + [EOS_token]
#             story.append(v)
#         # story = torch.Tensor(story)
#         return story
#
#     def preprocess_memory(self, sequence, word2idx):
#         """Converts words to ids."""
#         story = []
#         for value in sequence:
#             d, s, v = value
#             s = s.replace("book", "").strip()
#             # separate each word in value to different memory slot
#             for wi, vw in enumerate(v.split()):
#                 idx = [word2idx[word] if word in word2idx else UNK_token for word in [d, s, "t{}".format(wi), vw]]
#                 story.append(idx)
#         story = torch.Tensor(story)
#         return story
#
#     def preprocess_domain(self, turn_domain):
#         domains = {"attraction": 0, "restaurant": 1, "taxi": 2, "train": 3, "hotel": 4, "hospital": 5, "bus": 6,
#                    "police": 7}
#         return domains[turn_domain]
#
#
# def collate_fn(data):
#     def merge(sequences):
#         '''
#         merge from batch * sent_len to batch * max_len
#         sequences: list of tensors
#         '''
#         lengths = [len(seq) for seq in sequences]
#         max_len = 1 if max(lengths) == 0 else max(lengths)
#         padded_seqs = torch.ones(len(sequences), max_len).long()
#         for i, seq in enumerate(sequences):
#             end = lengths[i]
#             padded_seqs[i, :end] = seq[:end]
#         padded_seqs = padded_seqs.detach()  # torch.tensor(padded_seqs)
#         return padded_seqs, lengths
#
#     def merge_multi_response(sequences):
#         '''
#         merge from batch * nb_slot * slot_len to batch * nb_slot * max_slot_len
#         sequences: list of lists [bsz, 30, slot_len]
#         '''
#         lengths = []
#         for bsz_seq in sequences:
#             length = [len(v) for v in bsz_seq]
#             lengths.append(length)
#         max_len = max([max(l) for l in lengths])
#         padded_seqs = []
#         for bsz_seq in sequences:
#             pad_seq = []
#             for v in bsz_seq:
#                 v = v + [PAD_token] * (max_len - len(v))
#                 pad_seq.append(v)
#             padded_seqs.append(pad_seq)
#         padded_seqs = torch.tensor(padded_seqs)
#         lengths = torch.LongTensor(lengths)
#         return padded_seqs, lengths
#
#     def merge_memory(sequences):
#         lengths = [len(seq) for seq in sequences]
#         max_len = 1 if max(lengths) == 0 else max(lengths)  # avoid the empty belief state issue
#         padded_seqs = torch.ones(len(sequences), max_len, 4).long()
#         for i, seq in enumerate(sequences):
#             end = lengths[i]
#             if len(seq) != 0:
#                 padded_seqs[i, :end, :] = seq[:end]
#         return padded_seqs, lengths
#
#     # sort a list by sequence length (descending order) to use pack_padded_sequence
#     data.sort(key=lambda x: len(x['context']), reverse=True)
#     item_info = {}
#     for key in data[0].keys():
#         item_info[key] = [d[key] for d in data]
#
#     # merge sequences
#     src_seqs, src_lengths = merge(item_info['context'])
#     y_seqs, y_lengths = merge_multi_response(item_info["generate_y"])
#     gating_label = torch.tensor(item_info["gating_label"])
#     turn_domain = torch.tensor(item_info["turn_domain"])
#
#     if USE_CUDA:
#         src_seqs = src_seqs.cuda()
#         gating_label = gating_label.cuda()
#         turn_domain = turn_domain.cuda()
#         y_seqs = y_seqs.cuda()
#         y_lengths = y_lengths.cuda()
#         # src_lengths = src_lengths.cuda()
#
#     item_info["context"] = src_seqs
#     item_info["context_len"] = src_lengths
#     item_info["gating_label"] = gating_label
#     item_info["turn_domain"] = turn_domain
#     item_info["generate_y"] = y_seqs
#     item_info["y_lengths"] = y_lengths
#     return item_info
#
#
# def read_langs(file_name, gating_dict, SLOTS, dataset, lang, mem_lang, sequicity, training, max_line=None,
#                switch_exceptd=True, use_bert=False):
#     print(("Reading from {}".format(file_name)))
#     data = []
#     max_resp_len, max_value_len = 0, 0
#     domain_counter = {}
#     with open(file_name) as f:
#         dials = json.load(f)
#         # create vocab first
#         for dial_dict in dials:
#             if (args["all_vocab"] or dataset == "train") and training:
#                 for ti, turn in enumerate(dial_dict["dialogue"]):
#                     lang.index_words(tokenizer.tokenize(turn["system_transcript"]), 'utter')
#                     lang.index_words(tokenizer.tokenize(turn["transcript"]), 'utter')
#                     # mem_lang.index_words(turn["belief_state"], 'belief')
#
#         # determine training data ratio, default is 100%
#         if training and dataset == "train" and args["data_ratio"] != 100:
#             random.Random(10).shuffle(dials)
#             dials = dials[:int(len(dials) * 0.01 * args["data_ratio"])]
#
#         # shuffle the dials to avoid overfitting
#         random.Random(10).shuffle(dials)
#
#         cnt_lin = 1
#         for dial_dict in dials:
#             if use_bert:
#                 dialog_history = ["[CLS]"]
#             else:
#                 dialog_history = ""
#             last_belief_dict = {}
#             # Filtering and counting domains
#             for domain in dial_dict["domains"]:
#                 if domain not in EXPERIMENT_DOMAINS:
#                     continue
#                 if domain not in domain_counter.keys():
#                     domain_counter[domain] = 0
#                 if dial_dict["domains"] not in COMBINED_DOMAINS:
#                     COMBINED_DOMAINS.append(dial_dict["domains"])
#                 domain_counter[domain] += 1
#
#             # Unseen domain setting
#             if args["only_domain"] != "" and args["only_domain"] not in dial_dict["domains"]:
#                 continue
#             if (args["except_domain"] != "" and dataset == "test" and args["except_domain"] not in dial_dict[
#                 "domains"]) or \
#                     (args["except_domain"] != "" and dataset != "test" and [args["except_domain"]] == dial_dict[
#                         "domains"]):
#                 continue
#
#             if args["source_domain"] != "" and not set(args["source_domain"]) == set(dial_dict["domains"]):
#                 continue
#
#             # Reading data
#             for ti, turn in enumerate(dial_dict["dialogue"]):
#                 turn_domain = turn["domain"]
#                 turn_id = turn["turn_idx"]
#                 if use_bert:
#                     turn_uttr = tokenizer.tokenize(turn["system_transcript"] + " ; " + turn["transcript"] ) + ["[SEP]"]
#                 else:
#                     turn_uttr = turn["system_transcript"] + " ; " + turn["transcript"]
#                 turn_uttr_strip = turn_uttr
#                 if use_bert:
#                     if "[SEP]" in dialog_history:
#                         dialog_history.remove("[SEP]")
#                     dialog_history += tokenizer.tokenize(turn["system_transcript"] + " ; " + turn["transcript"] ) +  ["[SEP]"]
#                 else:
#                     dialog_history += (turn["system_transcript"] + " ; " + turn["transcript"] + " ; ")
#                 source_text = dialog_history
#                 turn_belief_dict = fix_general_label_error(turn["belief_state"], False, SLOTS)
#
#                 # Generate domain-dependent slot list
#                 slot_temp = SLOTS
#                 if dataset == "train" or dataset == "dev":
#                     if args["except_domain"] != "":
#                         slot_temp = [k for k in SLOTS if args["except_domain"] not in k]
#                         turn_belief_dict = OrderedDict(
#                             [(k, v) for k, v in turn_belief_dict.items() if args["except_domain"] not in k])
#                     elif args["only_domain"] != "":
#                         slot_temp = [k for k in SLOTS if args["only_domain"] in k]
#                         turn_belief_dict = OrderedDict(
#                             [(k, v) for k, v in turn_belief_dict.items() if args["only_domain"] in k])
#                     elif args["source_domain"] != "":
#                         slot_temp = [k for k in SLOTS for sourced in args["source_domain"] if sourced in k]
#                         turn_belief_dict = OrderedDict(
#                             [(k, v) for k, v in turn_belief_dict.items() for sourced in args["source_domain"] if
#                              sourced in k])
#                 else:
#                     if args["except_domain"] != "":
#                         slot_temp = [k for k in SLOTS if args["except_domain"] in k]
#                         turn_belief_dict = OrderedDict(
#                             [(k, v) for k, v in turn_belief_dict.items() if args["except_domain"] in k])
#                     elif args["only_domain"] != "":
#                         slot_temp = [k for k in SLOTS if args["only_domain"] in k]
#                         turn_belief_dict = OrderedDict(
#                             [(k, v) for k, v in turn_belief_dict.items() if args["only_domain"] in k])
#                     elif args["source_domain"] != "":
#                         slot_temp = [k for k in SLOTS for sourced in args["source_domain"] if sourced in k]
#                         turn_belief_dict = OrderedDict(
#                             [(k, v) for k, v in turn_belief_dict.items() for sourced in args["source_domain"] if
#                              sourced in k])
#
#                 turn_belief_list = [str(k) + '-' + str(v) for k, v in turn_belief_dict.items()]
#
#                 # if (args["all_vocab"] or dataset == "train") and training:
#                 #     mem_lang.index_words(turn_belief_dict, 'belief')
#
#                 class_label, generate_y, slot_mask, gating_label = [], [], [], []
#                 start_ptr_label, end_ptr_label = [], []
#                 # if switch_exceptd:
#                 for slot in slot_temp if switch_exceptd else SLOTS:  # using for meta experience-replay
#                     if slot in turn_belief_dict.keys():
#                         generate_y.append(turn_belief_dict[slot])
#
#                         if turn_belief_dict[slot] == "dontcare":
#                             gating_label.append(gating_dict["dontcare"])
#                         elif turn_belief_dict[slot] == "none":
#                             gating_label.append(gating_dict["none"])
#                         else:
#                             gating_label.append(gating_dict["ptr"])
#
#                         if max_value_len < len(turn_belief_dict[slot]):
#                             max_value_len = len(turn_belief_dict[slot])
#
#                     else:
#                         generate_y.append("none")
#                         gating_label.append(gating_dict["none"])
#
#                 data_detail = {
#                     "ID": dial_dict["dialogue_idx"],
#                     "domains": dial_dict["domains"],
#                     "turn_domain": turn_domain,
#                     "turn_id": turn_id,
#                     "dialog_history": source_text,
#                     "turn_belief": turn_belief_list,
#                     "gating_label": gating_label,
#                     "turn_uttr": turn_uttr_strip,
#                     'generate_y': generate_y
#                 }
#                 data.append(data_detail)
#
#                 if max_resp_len < len(source_text):
#                     max_resp_len = len(source_text)
#
#             cnt_lin += 1
#             if (max_line and cnt_lin >= max_line):
#                 break
#
#     # add t{} to the lang file
#     # if "t{}".format(max_value_len - 1) not in mem_lang.word2index.keys() and training:
#     #     for time_i in range(max_value_len):
#     #         mem_lang.index_words("t{}".format(time_i), 'utter')
#
#     print("domain_counter", domain_counter)
#     return data, max_resp_len, slot_temp
#
#
# def get_seq(pairs, lang, mem_lang, batch_size, type, sequicity):
#     if (type and args['fisher_sample'] > 0):
#         shuffle(pairs)
#         pairs = pairs[:args['fisher_sample']]
#
#     data_info = {}
#     data_keys = pairs[0].keys()
#     for k in data_keys:
#         data_info[k] = []
#
#     for pair in pairs:
#         for k in data_keys:
#             data_info[k].append(pair[k])
#
#     dataset = Dataset(data_info, lang.word2index, lang.word2index, sequicity, mem_lang.word2index)
#
#     if args["imbalance_sampler"] and type:
#         data_loader = torch.utils.data.DataLoader(dataset=dataset,
#                                                   batch_size=batch_size,  # * torch.cuda.device_count(),
#                                                   # shuffle=type,
#                                                   collate_fn=collate_fn,
#                                                   sampler=ImbalancedDatasetSampler(dataset))
#     else:
#         data_loader = torch.utils.data.DataLoader(dataset=dataset,
#                                                   batch_size=batch_size,  # * torch.cuda.device_count(),
#                                                   shuffle=type,
#                                                   collate_fn=collate_fn)
#     return data_loader
#
#
# def dump_pretrained_emb(word2index, index2word, dump_path):
#     print("Dumping pretrained embeddings...")
#     embeddings = [GloveEmbedding(), KazumaCharEmbedding()]
#     E = []
#     for i in tqdm(range(len(word2index.keys()))):
#         w = index2word[i]
#         e = []
#         for emb in embeddings:
#             e += emb.emb(w, default='zero')
#         E.append(e)
#     with open(dump_path, 'wt') as f:
#         json.dump(E, f)
#
#
# def get_slot_information(ontology):
#     ontology_domains = dict([(k, v) for k, v in ontology.items() if k.split("-")[0] in EXPERIMENT_DOMAINS])
#     SLOTS = [k.lower() for k in ontology_domains.keys()]
#     return SLOTS
#
#
# def prepare_data_seq_bert(training, task="dst", sequicity=0, batch_size=100, switch_exceptd=True, use_bert=False):
#     eval_batch = args["eval_batch"] if args["eval_batch"] else batch_size
#     file_train = 'data/train_dials.json'
#     file_dev = 'data/dev_dials.json'
#     file_test = 'data/test_dials.json'
#     # Create saving folder
#     if args['path']:
#         folder_name = args['path'].rsplit('/', 2)[0] + '/'
#     else:
#         folder_name = 'save/{}-'.format(args["decoder"]) + args["addName"] + args['dataset'] + str(args['task']) + '/'
#     print("folder_name", folder_name)
#     if not os.path.exists(folder_name):
#         os.makedirs(folder_name)
#     # load domain-slot pairs from ontology
#     ontology = json.load(open("data/multi-woz/MULTIWOZ2 2/ontology.json", 'r'))
#     ALL_SLOTS = get_slot_information(ontology)
#     gating_dict = {"ptr": 0, "dontcare": 1, "none": 2}
#     # Vocabulary
#     lang, mem_lang = Lang(), Lang()
#     lang.index_words(ALL_SLOTS, 'slot')
#     mem_lang.index_words(ALL_SLOTS, 'slot')
#     lang_name = 'lang-all.pkl' if args["all_vocab"] else 'lang-train.pkl'
#     mem_lang_name = 'mem-lang-all.pkl' if args["all_vocab"] else 'mem-lang-train.pkl'
#
#     if training:
#         pair_train, train_max_len, slot_train = read_langs(file_train, gating_dict, ALL_SLOTS, "train", lang, mem_lang,
#                                                            sequicity, training, switch_exceptd=switch_exceptd,
#                                                            use_bert=use_bert)
#         train = get_seq(pair_train, lang, mem_lang, batch_size, True, sequicity)
#         nb_train_vocab = lang.n_words
#         pair_dev, dev_max_len, slot_dev = read_langs(file_dev, gating_dict, ALL_SLOTS, "dev", lang, mem_lang, sequicity,
#                                                      training, use_bert=use_bert)
#         dev = get_seq(pair_dev, lang, mem_lang, eval_batch, False, sequicity)
#         pair_test, test_max_len, slot_test = read_langs(file_test, gating_dict, ALL_SLOTS, "test", lang, mem_lang,
#                                                         sequicity, training, use_bert=use_bert)
#         test = get_seq(pair_test, lang, mem_lang, eval_batch, False, sequicity)
#         if os.path.exists(folder_name + lang_name) and os.path.exists(folder_name + mem_lang_name):
#             print("[Info] Loading saved lang files...")
#             with open(folder_name + lang_name, 'rb') as handle:
#                 lang = pickle.load(handle)
#             with open(folder_name + mem_lang_name, 'rb') as handle:
#                 mem_lang = pickle.load(handle)
#         else:
#             print("[Info] Dumping lang files...")
#             with open(folder_name + lang_name, 'wb') as handle:
#                 pickle.dump(lang, handle)
#             with open(folder_name + mem_lang_name, 'wb') as handle:
#                 pickle.dump(mem_lang, handle)
#         emb_dump_path = 'data/emb{}.json'.format(len(lang.index2word))
#         if not os.path.exists(emb_dump_path) and args["load_embedding"]:
#             dump_pretrained_emb(lang.word2index, lang.index2word, emb_dump_path)
#     else:
#         with open(folder_name + lang_name, 'rb') as handle:
#             lang = pickle.load(handle)
#         with open(folder_name + mem_lang_name, 'rb') as handle:
#             mem_lang = pickle.load(handle)
#
#         pair_train, train_max_len, slot_train, train, nb_train_vocab = [], 0, {}, [], 0
#         pair_dev, dev_max_len, slot_dev = read_langs(file_dev, gating_dict, ALL_SLOTS, "dev", lang, mem_lang, sequicity,
#                                                      training)
#         dev = get_seq(pair_dev, lang, mem_lang, eval_batch, False, sequicity)
#         pair_test, test_max_len, slot_test = read_langs(file_test, gating_dict, ALL_SLOTS, "test", lang, mem_lang,
#                                                         sequicity, training)
#         test = get_seq(pair_test, lang, mem_lang, eval_batch, False, sequicity)
#
#     test_4d = []
#     if args['except_domain'] != "":
#         pair_test_4d, _, _ = read_langs(file_test, gating_dict, ALL_SLOTS, "dev", lang, mem_lang, sequicity, training)
#         test_4d = get_seq(pair_test_4d, lang, mem_lang, eval_batch, False, sequicity)
#
#     max_word = max(train_max_len, dev_max_len, test_max_len) + 1
#
#     print("Read %s pairs train" % len(pair_train))
#     print("Read %s pairs dev" % len(pair_dev))
#     print("Read %s pairs test" % len(pair_test))
#     print("Vocab_size: %s " % lang.n_words)
#     print("Vocab_size Training %s" % nb_train_vocab)
#     print("Vocab_size Belief %s" % mem_lang.n_words)
#     print("Max. length of dialog words for RNN: %s " % max_word)
#     print("USE_CUDA={}".format(USE_CUDA))
#
#     SLOTS_LIST = [ALL_SLOTS, slot_train, slot_dev, slot_test]
#     print("[Train Set & Dev Set Slots]: Number is {} in total".format(str(len(SLOTS_LIST[2]))))
#     print(SLOTS_LIST[2])
#     print("[Test Set Slots]: Number is {} in total".format(str(len(SLOTS_LIST[3]))))
#     print(SLOTS_LIST[3])
#     LANG = [lang, mem_lang]
#
#     return train, dev, test, test_4d, LANG, SLOTS_LIST, gating_dict, nb_train_vocab
#
#
# class ImbalancedDatasetSampler(torch.utils.data.sampler.Sampler):
#     """Samples elements randomly from a given list of indices for imbalanced dataset
#     Arguments:
#         indices (list, optional): a list of indices
#         num_samples (int, optional): number of samples to draw
#     """
#
#     def __init__(self, dataset, indices=None, num_samples=None):
#
#         # if indices is not provided,
#         # all elements in the dataset will be considered
#         self.indices = list(range(len(dataset))) \
#             if indices is None else indices
#
#         # if num_samples is not provided,
#         # draw `len(indices)` samples in each iteration
#         self.num_samples = len(self.indices) \
#             if num_samples is None else num_samples
#
#         # distribution of classes in the dataset
#         label_to_count = {}
#         for idx in self.indices:
#             label = self._get_label(dataset, idx)
#             if label in label_to_count:
#                 label_to_count[label] += 1
#             else:
#                 label_to_count[label] = 1
#
#         # weight for each sample
#         weights = [1.0 / label_to_count[self._get_label(dataset, idx)] for idx in self.indices]
#         self.weights = torch.DoubleTensor(weights)
#
#     def _get_label(self, dataset, idx):
#         return dataset.turn_domain[idx]
#
#     def __iter__(self):
#         return (self.indices[i] for i in torch.multinomial(self.weights, self.num_samples, replacement=True))
#
#     def __len__(self):
#         return self.num_samples

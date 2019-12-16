import torch
import torch.nn.functional as F

# constants
ALL_KERNELS = ['cosine', 'l1', 'l2']
ALL_POLICIES = ['1NN']


class DND():
    """The differentiable neural dictionary (DND) class. This enables episodic
    recall in a neural network.

    notes:
    - a memory is a row vector

    Parameters
    ----------
    dict_len : int
        the maximial len of the dictionary
    memory_dim : int
        the dim or len of memory i, we assume memory_i is a row vector
    kernel : str
        the metric for memory search

    Attributes
    ----------
    encoding_off : bool
        if True, stop forming memories
    retrieval_off : type
        if True, stop retrieving memories
    reset_memory : func;
        if called, clear the dictionary
    check_config : func
        check the class config

    """

    def __init__(self, dict_len, kernel='l2'):
        # params
        self.dict_len = dict_len
        self.kernel = kernel
        # dynamic state
        self.encoding_off = False
        self.retrieval_off = False
        # allocate space for memories
        self.reset_memory()
        # check everything
        self.check_config()

    def reset_memory(self):
        self.keys = []
        self.vals = []

    def check_config(self):
        assert self.dict_len > 0
        assert self.kernel in ALL_KERNELS

    def save_memory(self, memory_key, memory_val):
        """Save an episodic memory to the dictionary

        Parameters
        ----------
        memory_key : a row vector
            a DND key, used to for memory search
        memory_val : a row vector
            a DND value, representing the memory content
        """
        # add new memory to the the dictionary
        # get data is necessary for gradient reason
        self.keys.append(torch.squeeze(memory_key.data))
        self.vals.append(memory_val)


    def get_memory(self, query_key):
        """Perform a 1-NN search over dnd

        Parameters
        ----------
        query_key : a row vector
            a DND key, used to for memory search

        Returns
        -------
        a row vector
            a DND value, representing the memory content

        """
        # compute similarity(query, memory_i ), for all i
        similarities = compute_similarities(query_key, self.keys, self.kernel)
        # get the best-match memory
        best_memory_val = self._get_memory(similarities)
        return best_memory_val

    def _get_memory(self, similarities, policy='1NN'):
        """get the episodic memory according to some policy
        e.g. if the policy is 1nn, return the best matching memory
        e.g. the policy can be based on the rational model

        Parameters
        ----------
        similarities : a vector of len #memories
            the similarity between query vs. key_i, for all i
        policy : str
            the retrieval policy

        Returns
        -------
        a row vector
            a DND value, representing the memory content

        """
        best_memory_val = None
        if policy is '1NN':
            best_memory_id = torch.argmax(similarities)
            print('[info] the retrieval id is {}'.format(best_memory_id))
            best_memory_val = self.vals[best_memory_id]
        else:
            raise ValueError(f'unrecog recall policy: {policy}')
        return best_memory_val


"""helpers"""


def compute_similarities(query_key, key_list, metric):
    """Compute the similarity between query vs. key_i for all i
        i.e. compute q M, w/ q: 1 x key_dim, M: key_dim x #keys

    Parameters
    ----------
    query_key : a vector
        Description of parameter `query_key`.
    key_list : list
        Description of parameter `key_list`.
    metric : str
        Description of parameter `metric`.

    Returns
    -------
    a row vector w/ len #memories
        the similarity between query vs. key_i, for all i

    """
    # reshape query to 1 x key_dim
    q = query_key.data.view(1, -1)
    # reshape memory keys to #keys x key_dim
    M = torch.stack(key_list)
    # compute similarities
    # if metric is 'cosine':
    similarities = F.cosine_similarity(q, M)
    # elif metric is 'l1':
    #     similarities = - F.pairwise_distance(q, M, p=1)
    # elif metric is 'l2':
    # similarities = - F.pairwise_distance(q, M, p=2)
    # else:
    #     raise ValueError(f'unrecog metric: {metric}')
    return similarities



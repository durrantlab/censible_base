import molgrid
import torch
import torch.optim as optim
from _debug import grid_channel_to_xyz_file
import torch.nn as nn
import torch.nn.functional as F
from torch.nn import init
import numpy as np
from scipy.stats import pearsonr
from _training import View


class CENet(nn.Module):
    """Default 2018, but final layer generates coefficients for terms"""

    def __init__(self, dims, numterms=None):
        super(CENet, self).__init__()
        self.modules = []
        nchannels = dims[0]
        self.nterms = numterms
        self.func = F.relu

        avgpool1 = nn.AvgPool3d(2, stride=2)
        self.add_module("avgpool_0", avgpool1)
        self.modules.append(avgpool1)
        conv1 = nn.Conv3d(
            nchannels, out_channels=32, padding=1, kernel_size=3, stride=1
        )
        self.add_module("unit1_conv", conv1)
        self.modules.append(conv1)
        conv2 = nn.Conv3d(32, out_channels=32, padding=0, kernel_size=1, stride=1)
        self.add_module("unit2_conv", conv2)
        self.modules.append(conv2)
        avgpool2 = nn.AvgPool3d(2, stride=2)
        self.add_module("avgpool_1", avgpool2)
        self.modules.append(avgpool2)
        conv3 = nn.Conv3d(32, out_channels=64, padding=1, kernel_size=3, stride=1)
        self.add_module("unit3_conv", conv3)
        self.modules.append(conv3)
        conv4 = nn.Conv3d(64, out_channels=64, padding=0, kernel_size=1, stride=1)
        self.add_module("unit4_conv", conv4)
        self.modules.append(conv4)
        avgpool3 = nn.AvgPool3d(2, stride=2)
        self.add_module("avgpool_2", avgpool3)
        self.modules.append(avgpool3)
        conv5 = nn.Conv3d(64, out_channels=128, padding=1, kernel_size=3, stride=1)
        self.add_module("unit5_conv", conv5)
        self.modules.append(conv5)
        div = 2 * 2 * 2
        last_size = int(dims[1] // div * dims[2] // div * dims[3] // div * 128)
        # print(last_size)
        flattener = View((-1, last_size))
        self.add_module("flatten", flattener)
        self.modules.append(flattener)
        self.fc = nn.Linear(last_size, numterms)
        self.add_module("last_fc", self.fc)

    def forward(self, x, smina_terms):
        # should approximate the affinity of the receptor/ligand pair

        for layer in self.modules:
            x = layer(x)
            if isinstance(layer, nn.Conv3d):
                x = self.func(x)
        coef_predict = self.fc(x) / 1000  # JDD added
        batch_size, num_terms = coef_predict.shape

        # import pdb; pdb.set_trace()
        # Here also predict term * weight for each term. For another graph, that
        # isn't scaled.
        # coef_predict = coef_predict.view(batch_size, num_terms, -1)

        # Do batchwise, pairwise multiplication coef_predict and smina_terms
        contributions = coef_predict * smina_terms

        # batchwise dot product
        return (
            torch.bmm(
                coef_predict.view(batch_size, 1, num_terms),
                smina_terms.view(batch_size, num_terms, 1),
            ),
            coef_predict,
            contributions
        )

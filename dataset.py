from torch.utils.data import Dataset
import os
import numpy as np
from PIL import Image


class SingleLabelDataset(Dataset):
    def __init__(self, data_path_name, transform=None):
        self.path = data_path_name
        self.files = os.listdir(data_path_name)
        self.transform = transform

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        image_path = os.path.join(self.path, self.files[idx])
        im = Image.open(image_path)
        # im = im / 255 # convert to 0-1 scale
        if self.transform:
            im = self.transform(im)
        label = int(self.files[idx][-5:-4])
        return im, label


class OnlineDataset(Dataset):
    def __init__(self, data_path_name, transform=None):
        self.path = data_path_name
        self.files = os.listdir(data_path_name)
        self.transform = transform

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        image_path = os.path.join(self.path, self.files[idx])
        im = Image.open(image_path)
        im_list, position_list = onlinecutpatches(im)
        if self.transform:
            for patch_id in range(len(im_list)):
                im_list[patch_id] = self.transform(im_list[patch_id])
        # label = int(self.files[idx][-5:-4])
        # position = tuple(int(self.files[idx][-7]), int(self.files[idx][-8]))
        return image_path, im_list, position_list


def onlinecutpatches(im, im_size=56, stride=28):
    """
    function for crop the image to subpatches, will include corner cases
    the return position (x,y) is the up left corner of the image

    Args:
        im (np.ndarray): the image for cropping
        im_size (int, optional): the sub-image size. Defaults to 56.
        stride (int, optional): the pixels between two sub-images. Defaults to 28.

    Returns:
        (list, list): list of image reference and list of its corresponding positions
    """
    im_list = []
    position_list = []

    h, w, _ = im.shape

    h_ = np.arange(0, h-stride, stride)
    if h % stride != 0:
        h_ = np.append(h_, h-im_size)
    w_ = np.arange(0, w, stride)
    if w % stride != 0:
        w_ = np.append(w_, w-im_size)

    for i in h_:
        for j in w_:
            im_list.append(im[i:i+im_size,j:j+im_size])
            position_list.append((i,j))
    return im_list, position_list

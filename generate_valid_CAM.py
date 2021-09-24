import json
from PIL import Image
from tqdm import tqdm
from torchvision import transforms
import torch.nn.functional as F
import numpy as np
from torch.utils.data import DataLoader
import dataset
import network
import torch
from math import inf
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '2'

dataset_path = "./Dataset/2.validation/img"
model_name = ['secondphase_ep10', 'model_last', '9632_ep10', '01_best']
model_crop = [(96, 32), (56, 28), (96, 32), (225, 100)]

visualize_pick = [0, 7, 8, 9, 31, 34, 35, 39]

with open('groundtruth.json') as f:
    big_labels = json.load(f)

for i in range(4):
    net = network.ResNetCAM()
    path = "./modelstates/" + model_name[i] + ".pth"
    pretrained = torch.load(path)['model']
    if i != 1:  # only exception is the model_last
        pretrained = {k[7:]: v for k, v in pretrained.items()}
    pretrained['fc1.weight'] = pretrained['fc1.weight'].unsqueeze(
        -1).unsqueeze(-1).to(torch.float64)
    pretrained['fc2.weight'] = pretrained['fc2.weight'].unsqueeze(
        -1).unsqueeze(-1).to(torch.float64)

    net.load_state_dict(pretrained)
    print(f'Model loaded from {path} Successfully')
    net.cuda()
    net.eval()

    side_length = model_crop[i][0]
    stride = model_crop[i][1]
    onlineDataset = dataset.OnlineDataset(dataset_path, transform=transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])]),
        patch_size=side_length,
        stride=stride)

    onlineDataloader = DataLoader(onlineDataset, batch_size=1, drop_last=False)

    for im_path, im_list, position_list in tqdm(onlineDataloader):
        if int(im_path[0][-6:-4]) not in visualize_pick:
            continue

        orig_img = np.asarray(Image.open(im_path[0]))

        def tocamlist(im):
            im = im.cuda()
            cam_scores = net(im)
            cam_scores = F.interpolate(cam_scores, (side_length, side_length), mode='bilinear', align_corners=False)[0].detach().cpu().numpy()
            return cam_scores

        cam_list = list(map(tocamlist, im_list))

        sum_cam = np.zeros((3, orig_img.shape[0], orig_img.shape[1]))
        sum_counter = np.zeros_like(sum_cam)
        for i in range(len(cam_list)):
            y, x = position_list[i][0], position_list[i][1]
            crop = cam_list[i]
            sum_cam[:, y:y+side_length, x:x+side_length] += crop
            sum_counter[:, y:y+side_length, x:x+side_length] += 1
        sum_counter[sum_counter < 1] = 1

        sum_cam = sum_cam / sum_counter

        # are these four lines useful?
        cam_max = np.max(sum_cam, (1, 2), keepdims=True)
        cam_min = np.min(sum_cam, (1, 2), keepdims=True)
        sum_cam[sum_cam < cam_min+1e-5] = 0
        norm_cam = (sum_cam-cam_min) / (cam_max - cam_min + 1e-5)

        big_label = big_labels[im_path[0][-6:]]
        for i in range(3):
            if big_label[i] == 0:
                norm_cam[i, :, :] = -inf
        result_label = norm_cam.argmax(axis=0)

        if not os.path.exists('out_cam'):
            os.mkdir('out_cam')

        if not os.path.exists(f'out_cam/{model_name}'):
            os.mkdir(f'out_cam/{model_name}')
        np.save(f'out_cam/{model_name}/{im_path[0][-6:-4]}.npy', result_label)

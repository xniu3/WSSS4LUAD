import json
from PIL import Image
from tqdm import tqdm
from torchvision import transforms
import torch.nn.functional as F
import numpy as np
from torch.utils.data import DataLoader
import dataset
import torch
import os
from scipy.stats import mode

# IMPORTANT! Note we DO NOT use the norm in all cases.

def generate_validation_cam(net, side_length, batch_size, resize, dataset_path, cam_folder_name, model_name, scales, elimate_noise=False, label_path=None, majority_vote=False):
    """
    generate the class activation map using the model pass into

    Args:
        net (torch.models): the classification model
        side_length (int)
        batch_size (int): batch to process the cam
        resize (int): the size image is changed to
        dataset_path (string): the address of the image dataset
        cam_folder_name (string): the folder to store the cam output
        model_name (string): the name for this cam_output model
        scales (list): a list of different scales to do model ensemble
        eliminate_noise: if use image-level label to cancel some of the noise
        label_path (string): if `eliminate_noise` is True, input the labels path
        majority_vote (bool): whether to use the majortity vote to ensemble
    """

    net.cuda()
    net.eval()

    crop_image_path = f'{cam_folder_name}/crop_images/'
    image_name_list = os.listdir(crop_image_path)
    extension_name = os.listdir(dataset_path)[0].split('.')[-1]
    
    for image_name in tqdm(image_name_list):
        orig_img = np.asarray(Image.open(f'{dataset_path}/{image_name}.{extension_name}'))
        w, h, _ = orig_img.shape
        if majority_vote:
            ensemble_cam = []
        else:
            ensemble_cam = np.zeros((3, w, h))
        
        for scale in scales:
            image_per_scale_path = crop_image_path + image_name + '/' + str(scale)
            scale = float(scale)
            offlineDataset = dataset.OfflineDataset(image_per_scale_path, transform=transforms.Compose([
                    transforms.Resize((resize,resize)),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.678,0.505,0.735], std=[0.144,0.208,0.174])
                ])
            )
            offlineDataloader = DataLoader(offlineDataset, batch_size=batch_size, drop_last=False)

            w_ = int(w*scale)
            h_ = int(h*scale)
            interpolatex = side_length
            interpolatey = side_length
            if w_ < side_length:
                interpolatex = w_
            if h_ < side_length:
                interpolatey = h_

            with torch.no_grad():
                cam_list = []
                position_list = []
                for ims, positions in offlineDataloader:
                    cam_scores = net(ims.cuda())
                    cam_scores = F.interpolate(cam_scores, (interpolatex, interpolatey), mode='bilinear', align_corners=False).detach().cpu().numpy()
                    cam_list.append(cam_scores)
                    position_list.append(positions.numpy())
                cam_list = np.concatenate(cam_list)
                position_list = np.concatenate(position_list)
                sum_cam = np.zeros((3, w_, h_))
                sum_counter = np.zeros_like(sum_cam)
                
                for k in range(cam_list.shape[0]):
                    y, x = position_list[k][0], position_list[k][1]
                    crop = cam_list[k]
                    sum_cam[:, y:y+side_length, x:x+side_length] += crop
                    sum_counter[:, y:y+side_length, x:x+side_length] += 1
                sum_counter[sum_counter < 1] = 1
                norm_cam = sum_cam / sum_counter
                norm_cam = F.interpolate(torch.unsqueeze(torch.tensor(norm_cam),0), (w, h), mode='bilinear', align_corners=False).detach().cpu().numpy()[0]

                # use the image-level label to eliminate impossible pixel classes
                if majority_vote:
                    if elimate_noise:
                        with open(f'val_image_label/{label_path}') as f:
                            big_labels = json.load(f)
                        big_label = big_labels[f'{image_name}.png']        
                        for k in range(3):
                            if big_label[k] == 0:
                                norm_cam[k, :, :] = -np.inf
                
                    norm_cam = np.argmax(norm_cam, axis=0)        
                    ensemble_cam.append(norm_cam)
                else:
                    ensemble_cam += norm_cam                
        
        if majority_vote:
            ensemble_cam = np.stack(ensemble_cam, axis=0)
            result_label = mode(ensemble_cam, axis=0)[0]
        else:
            if elimate_noise:
                with open(f'val_image_label/{label_path}') as f:
                    big_labels = json.load(f)
                big_label = big_labels[f'{image_name}.png']        
                for k in range(3):
                    if big_label[k] == 0:
                        ensemble_cam[k, :, :] = -np.inf
                        
            result_label = ensemble_cam.argmax(axis=0)

        if not os.path.exists(f'{cam_folder_name}/{model_name}'):
            os.mkdir(f'{cam_folder_name}/{model_name}')
        np.save(f'{cam_folder_name}/{model_name}/{image_name}.npy', result_label)
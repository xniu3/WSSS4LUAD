import numpy as np
import os
from matplotlib import pyplot as plt
from tqdm import tqdm
import png
from PIL import Image
from utils.metric import get_mIOU

def visualize_result(model_name):
    """
    get the 0,1,2,3 predictions from directory out_cam/{model_name} and compare with groundtruth
    will generate some temporary files

    Args:
        model_names (list): list of results you want to test on validation set
    """
    img_path = 'Dataset/2.validation/img'
    gt_path = 'Dataset/2.validation/mask'
    mask_path = 'Dataset/2.validation/background-mask'

    if not os.path.exists(f'temp2'):
        os.mkdir(f'temp2')

    visualize_pick = np.arange(40) # define the id of images that require visualization
    
    for i in tqdm(visualize_pick):
        
        mask = np.asarray(Image.open(mask_path + f'/{i:02d}.png'))
        
        cam_path = f'valid_out_cam/{model_name}'
        cam = np.load(os.path.join(cam_path, f'{i:02d}.npy'), allow_pickle=True).astype(np.uint8)
        
        groundtruth = np.asarray(Image.open(gt_path + f'/{i:02d}.png'))
        
        score = get_mIOU(mask, groundtruth, cam)

        palette = [(0, 64, 128), (64, 128, 0), (243, 152, 0), (255, 255, 255)]
        # with open(f'temp/{i:02d}.png', 'wb') as f:
        #     w = png.Writer(cam.shape[1], cam.shape[0], palette=palette, bitdepth=8)
        #     w.write(f, cam)

        cam[mask == 1] = 3
        with open(f'temp/{i:02d}.png', 'wb') as f:
            w = png.Writer(cam.shape[1], cam.shape[0],palette=palette, bitdepth=8)
            w.write(f, cam)

        cam_path2 = 'valid_out_cam/resnet_newnorm_last'
        cam2 = np.load(os.path.join(cam_path2, f'{i:02d}.npy'), allow_pickle=True).astype(np.uint8)
        cam2[mask == 1] = 3
        with open(f'temp2/{i:02d}.png', 'wb') as f:
            w = png.Writer(cam2.shape[1], cam2.shape[0],palette=palette, bitdepth=8)
            w.write(f, cam2)
        

        plt.figure(i, figsize=(40, 40))
        im = plt.imread(f'temp/{i:02d}.png')
        gt = plt.imread(gt_path + f'/{i:02d}.png')
        prediction2 = plt.imread(f'temp2/{i:02d}.png')
        plt.subplot(221)
        plt.imshow(im)
        plt.title('prediction of cutmix')
        plt.subplot(222)
        plt.imshow(prediction2)
        plt.title('prediction of baseline')
        plt.subplot(223)
        plt.imshow(gt)
        plt.title('groundtruth')
        plt.savefig(f'temp/{i:02d}.png')

        # plt.figure(i)
        # im = plt.imread(f'temp/{i:02d}.png')
        # im_mask = plt.imread(f'temp/{i:02d}_1.png')
        # gt = plt.imread(gt_path + f'/{i:02d}.png')
        # origin = plt.imread(img_path + f'/{i:02d}.png')

        # plt.figure(i, figsize=(40, 40))
        # plt.subplot(2, 2, 1)
        # plt.imshow(im)
        # plt.title(f'cam, mIOU = {score:.2f}')
        # plt.subplot(2, 2, 2)
        # plt.imshow(gt)
        # plt.title('groundtruth')
        # plt.subplot(2, 2, 3)
        # plt.imshow(origin)
        # plt.title('origin image')
        # plt.subplot(2, 2, 4)
        # plt.imshow(im_mask)
        # plt.title('cam with background mask')

        # if not os.path.exists(f'{model_name}_heatmap'):
        #     os.mkdir(f'{model_name}_heatmap')

        # plt.savefig(f'{model_name}_heatmap/{i:02d}.png')
        # plt.close()

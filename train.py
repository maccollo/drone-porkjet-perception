"""Training script for detector."""
from __future__ import print_function

import argparse
from datetime import datetime
import os

import torch
from torch import nn
from torchvision.datasets import CocoDetection
import torchvision.transforms.functional as TF
from PIL import Image
import matplotlib.pyplot as plt
import wandb

import utils
from detector import Detector

NUM_CATEGORIES = 15


def train(device="cpu"):
    """Train the network.

    Args:
        device: The device to train on."""

    wandb.init(project="detector_baseline")

    # Init model
    detector = Detector().to(device)

    wandb.watch(detector)

    dataset = CocoDetection(
        root="./dd2419_coco/training",
        annFile="./dd2419_coco/annotations/training.json",
        transforms=detector.input_transform,
    )
    datasetValidation = CocoDetection(
        root="./dd2419_coco/validation",
        annFile="./dd2419_coco/annotations/validation.json",
        transforms=detector.input_transform,
    )

    dataloader = torch.utils.data.DataLoader(dataset, batch_size=8, shuffle=True)
    dataloadervalidation = torch.utils.data.DataLoader(datasetValidation, batch_size=8, shuffle=True)
    # training params
    max_iterations = wandb.config.max_iterations = 30000
    learning_rate = wandb.config.learning_rate = 1e-4
    weight_reg = wandb.config.weight_reg = 1
    weight_noobj = wandb.config.weight_noobj = 1
    weight_sign = wandb.config.weight_noobj = 1

    # run name (to easily identify model later)
    time_string = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    run_name = wandb.config.run_name = "det_{}".format(time_string)

    # init optimizer
    optimizer = torch.optim.Adam(detector.parameters(), lr=learning_rate)

    # load test images
    # these will be evaluated in regular intervals
    category_dict = [
        {
            "id": 0,
            "name": "no bicycle",
            "supercategory": "traffic sign"
        },
        {
            "id": 1,
            "name": "airport",
            "supercategory": "traffic sign"
        },
        {
            "id": 2,
            "name": "dangerous left",
            "supercategory": "traffic sign"
        },
        {
            "id": 3,
            "name": "dangerous right",
            "supercategory": "traffic sign"
        },
        {
            "id": 4,
            "name": "follow left",
            "supercategory": "traffic sign"
        },
        {
            "id": 5,
            "name": "follow right",
            "supercategory": "traffic sign"
        },
        {
            "id": 6,
            "name": "junction",
            "supercategory": "traffic sign"
        },
        {
            "id": 7,
            "name": "no heavy truck",
            "supercategory": "traffic sign"
        },
        {
            "id": 8,
            "name": "no parking",
            "supercategory": "traffic sign"
        },
        {
            "id": 9,
            "name": "no stopping and parking",
            "supercategory": "traffic sign"
        },
        {
            "id": 10,
            "name": "residential",
            "supercategory": "traffic sign"
        },
        {
            "id": 11,
            "name": "narrows from left",
            "supercategory": "traffic sign"
        },
        {
            "id": 12,
            "name": "narrows from right",
            "supercategory": "traffic sign"
        },
        {
            "id": 13,
            "name": "roundabout",
            "supercategory": "traffic sign"
        },
        {
            "id": 14,
            "name": "stop",
            "supercategory": "traffic sign"
        }
    ]
    test_images = []
    show_test_images = False
    directory = "./test_images"
    if not os.path.exists(directory):
        os.makedirs(directory)
    for file_name in sorted(os.listdir(directory)):
        if file_name.endswith(".jpg"):
            file_path = os.path.join(directory, file_name)
            test_image = Image.open(file_path)
            torch_image, _ = detector.input_transform(test_image, [])
            test_images.append(torch_image)

    if test_images:
        test_images = torch.stack(test_images)
        test_images = test_images.to(device)
        show_test_images = True

    print("Training started...")

    current_iteration = 1
    while current_iteration <= max_iterations:
        for img_batch, target_batch in dataloader:
            img_batch = img_batch.to(device)
            target_batch = target_batch.to(device)

            # run network
            out = detector(img_batch)

            # positive / negative indices
            # (this could be passed from input_transform to avoid recomputation)
            pos_indices = torch.nonzero(target_batch[:, 4, :, :] == 1, as_tuple=True)
            neg_indices = torch.nonzero(target_batch[:, 4, :, :] == 0, as_tuple=True)


            # compute loss
            sign_mse = nn.functional.mse_loss(
                out[pos_indices[0], 5:19, pos_indices[1], pos_indices[2]],
                target_batch[pos_indices[0], 5:19, pos_indices[1], pos_indices[2]],
            )
            reg_mse = nn.functional.mse_loss(
                out[pos_indices[0], 0:4, pos_indices[1], pos_indices[2]],
                target_batch[pos_indices[0], 0:4, pos_indices[1], pos_indices[2]],
            )
            pos_mse = nn.functional.mse_loss(
                out[pos_indices[0], 4, pos_indices[1], pos_indices[2]],
                target_batch[pos_indices[0], 4, pos_indices[1], pos_indices[2]],
            )
            neg_mse = nn.functional.mse_loss(
                out[neg_indices[0], 4, neg_indices[1], neg_indices[2]],
                target_batch[neg_indices[0], 4, neg_indices[1], neg_indices[2]],
            )
            loss = pos_mse + weight_reg * reg_mse + weight_noobj * neg_mse + sign_mse*weight_sign

            # optimize
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            #Here we do 
            #wandb.log(
            #    {
            #        "total loss": loss.item(),
            #        "loss pos": pos_mse.item(),
            #        "loss neg": neg_mse.item(),
            #        "loss reg": reg_mse.item(),
            #    },
            #    step=current_iteration,
            #)

            print(
                "Iteration: {}, loss: {}".format(current_iteration, loss.item()),
            )

            # generate visualization every N iterations
            if current_iteration % 250 == 0 and show_test_images:
                detector.eval()
                with torch.no_grad():
                    out = detector(test_images).cpu()
                    bbs = detector.decode_output(out, 0.5)

                    for i, test_image in enumerate(test_images):
                        figure, ax = plt.subplots(1)
                        plt.imshow(test_image.cpu().permute(1, 2, 0))
                        plt.imshow(
                            out[i, 4, :, :],
                            interpolation="nearest",
                            extent=(0, 640, 480, 0),
                            alpha=0.7,
                        )

                        # add bounding boxes
                        utils.add_bounding_boxes(ax, bbs[i],category_dict)

                        wandb.log(
                            {"test_img_{i}".format(i=i): figure}, step=current_iteration
                        )
                        plt.close()
                detector.train()
                
            current_iteration += 1
        if current_iteration > max_iterations:
            break
        valid_loss_total = 0.0
        valid_loss_pos = 0.0
        valid_loss_neg = 0.0
        valid_loss_reg = 0.0
        validationIteration = 0
        for img_batch, target_batch in dataloadervalidation:
            img_batch = img_batch.to(device)
            target_batch = target_batch.to(device)
                
            # Forward Pass
            out = detector(img_batch)
            # Calculate Loss
            # positive / negative indices
            # (this could be passed from input_transform to avoid recomputation)
            pos_indices = torch.nonzero(target_batch[:, 4, :, :] == 1, as_tuple=True)
            neg_indices = torch.nonzero(target_batch[:, 4, :, :] == 0, as_tuple=True)
            # compute loss
            sign_mse = nn.functional.mse_loss(
                out[pos_indices[0], 5:19, pos_indices[1], pos_indices[2]],
                target_batch[pos_indices[0], 5:19, pos_indices[1], pos_indices[2]],
            )
            reg_mse = nn.functional.mse_loss(
                out[pos_indices[0], 0:4, pos_indices[1], pos_indices[2]],
                target_batch[pos_indices[0], 0:4, pos_indices[1], pos_indices[2]],
            )
            pos_mse = nn.functional.mse_loss(
                out[pos_indices[0], 4, pos_indices[1], pos_indices[2]],
                target_batch[pos_indices[0], 4, pos_indices[1], pos_indices[2]],
            )
            neg_mse = nn.functional.mse_loss(
                out[neg_indices[0], 4, neg_indices[1], neg_indices[2]],
                target_batch[neg_indices[0], 4, neg_indices[1], neg_indices[2]],
            )
            loss = pos_mse + weight_reg * reg_mse + weight_noobj * neg_mse + sign_mse*weight_sign
            validationIteration += 1
            print(
                "Validation irreteration: {}, loss: {}".format(validationIteration, valid_loss_total),
            )
        wandb.log(
            {
                "total loss": valid_loss_total,
                "loss pos": valid_loss_pos,
                "loss neg": valid_loss_neg,
                "loss reg": valid_loss_reg,
            },
            step=current_iteration,
        )

    print("\nTraining completed (max iterations reached)")

    model_path = "{}.pt".format(run_name)
    utils.save_model(detector, model_path)
    wandb.save(model_path)

    print("Model weights saved at {}".format(model_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    device = parser.add_mutually_exclusive_group(required=True)
    device.add_argument("--cpu", dest="device", action="store_const", const="cpu")
    device.add_argument("--gpu", dest="device", action="store_const", const="cuda")
    args = parser.parse_args()
    train(args.device)
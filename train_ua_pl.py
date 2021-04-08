import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import argparse
from PIL import Image
import os
import pandas as pd
from sklearn.metrics import r2_score, mean_squared_error

from torch.utils.data import Dataset
import matplotlib.pyplot as plt

from pytorchtools import EarlyStopping
import random

# # Hyper parameters
# num_epochs = 10
# num_classes = 24
# batch_size = 128
# learning_rate = 0.001

# Set deterministic random seed
random_seed = 999
torch.manual_seed(random_seed)
torch.cuda.manual_seed(random_seed)
torch.cuda.manual_seed_all(random_seed) # if use multi-GPU
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
np.random.seed(random_seed)
random.seed(random_seed)

## TRAIN
DATAPATH_TRAIN = os.path.join('data', 'train')
DATASETS_TRAIN = [
    'binary_501',
    'binary_502',
    'binary_503',
    'binary_504',
    'binary_505',
    'binary_506',
    'binary_507',
    'binary_508',
    'binary_509',
    'binary_510',
    'binary_511',
    'binary_512',
    'binary_1001',
    'binary_1002',
    'binary_1003',
    'binary_rl_fix_501',
    'binary_rl_fix_502',
    'binary_rl_fix_503',
    'binary_rl_fix_504',
    'binary_rl_fix_505',
    'binary_rl_fix_506',
    'binary_rl_fix_507',
    'binary_rl_fix_508',
    'binary_rl_fix_509',
    'binary_rl_fix_510',
    'binary_rl_fix_511',
    'binary_rl_fix_512',
    'binary_rl_fix_513',
    'binary_rl_fix_514',
    'binary_rl_fix_515',
    'binary_rl_fix_516',
    'binary_rl_fix_517',
    'binary_rl_fix_518',
    'binary_rl_fix_519',
    'binary_rl_fix_520',
    'binary_rl_fix_1001',
    'binary_rl_fix_1002',
    'binary_rl_fix_1003',
    'binary_rl_fix_1004',
    'binary_rl_fix_1005',
    'binary_rl_fix_1006',
    'binary_rl_fix_1007',
    'binary_rl_fix_1008',
]

## VALIDATION
DATAPATH_VALID = './data/valid'
DATASETS_VALID = [
    'binary_1004',
    'binary_test_1001',
    'binary_test_1002',
    'binary_rl_fix_1009',
    'binary_rl_fix_1010',
    'binary_rl_fix_1011',
    'binary_rl_fix_1012',
    'binary_rl_fix_1013',
    'binary_rl_fix_test_1001',
]

## TEST
DATAPATH_TEST = './data/test'
DATASETS_TEST = [
    'binary_new_test_501',
    'binary_new_test_1501',
    'binary_rl_fix_1014',
    'binary_rl_fix_1015',
    'binary_rl_fix_test_1002',
    'binary_rl_fix_test_1003',
    'binary_rl_fix_test_1004',
    'binary_rl_fix_test_1005',
    'binary_test_1101',
]


class MaxwellFDFDDataset(Dataset):
    def __init__(self, data, target, transform=None):
        self.data = torch.from_numpy(data).float()
        self.target = torch.from_numpy(target).float()
        self.transform = transform

    def __getitem__(self, index):
        x = self.data[index]
        y = self.target[index]

        return x, y

    def __len__(self):
        return len(self.data)


def scatter_plot(y_true, y_pred, message, result_path, iter_number, model_number):
    result = np.column_stack((y_true,y_pred))

    if not os.path.exists('{}/{}'.format(result_path, 'csv')):
        os.makedirs('{}/{}'.format(result_path, 'csv'))

    if not os.path.exists('{}/{}'.format(result_path, 'scatter')):
        os.makedirs('{}/{}'.format(result_path, 'scatter'))

    pd.DataFrame(result).to_csv("{}/csv/{}_{}.csv".format(result_path, iter_number, model_number), index=False)

    plt.clf()
    plt.scatter(y_pred, y_true, s=3)
    plt.suptitle(message)
    plt.xlabel('Predictions')
    plt.ylabel('Actual')
    plt.savefig("{}/scatter/{}_{}.png".format(result_path, iter_number, model_number))

print('Converting to TorchDataset...')

def mse_loss(input, target):
    return ((input - target) ** 2).sum() / input.data.nelement()

def sqrt_loss(input, target):
    return ((input-target) ** 0.5).sum() / input.data.nelement()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--loss_function", help="Select loss functions.. (rmse,diff_rmse,diff_ce)", default="rmse")
    parser.add_argument("-lr", "--learning_rate", help="Set learning_rate", type=float, default=0.001)
    parser.add_argument("-e", "--max_epoch", help="Set max epoch", type=int, default=10)
    parser.add_argument("-b", "--batch_size", help="Set batch size", type=int, default=32)

    # arg for testing parameters
    parser.add_argument("-u", "--unit_test", help="flag for testing source code", action='store_true')
    parser.add_argument("-d", "--debug", help="flag for debugging", action='store_true')

    parser.add_argument("-o", "--optimizer", help="Select optimizer.. (sgd, adam, adamw)", default='adam')
    parser.add_argument("-bn", "--is_batch_norm", help="Set is_batch_norm", action='store_true')
    # arg for AL
    parser.add_argument("-it", "--iteration", help="Set iteration for AL", type=int, default=1)
    parser.add_argument("-n", "--num_models", help="Set number of models for active regressors", type=int, default=3)
    parser.add_argument("-a", "--is_active_learning", help="Set is AL", action='store_true')
    parser.add_argument("-ar", "--is_active_random", help="Set is AL random set", action='store_true')
    parser.add_argument("-k", "--sample_number", help="Set K", type=int, default=500)
    parser.add_argument("-ll", "--loss_lambda", help="set loss lambda", type=float, default=0.5)
    parser.add_argument("-rtl", "--rpo_type_lambda", help="max random data ratio", type=float, default=0.5)

    # arg for KD
    parser.add_argument("-rm", "--remember_model", action='store_true')
    parser.add_argument("-w", "--weight", action='store_true')
    parser.add_argument("-tor", "--teacher_outlier_rejection", action='store_true')
    parser.add_argument("-tbr", "--teacher_bounded_regression", action='store_true')
    parser.add_argument("-tbra", "--tbr_addition", action='store_true')
    parser.add_argument("-z", "--z_score", type=float, default=2.0)
    parser.add_argument("-pl", "--pseudo_label", action='store_true')
    # arg for rpo type
    parser.add_argument("-rt", "--rpo_type", help="Select rpo type.. (max_diff, min_diff, random, pl)", default='pl')

    # arg for uncertainty attention
    parser.add_argument("-ua", "--uncertainty_attention", help="flag for uncertainty attention of gradients", action='store_true')

    parser.add_argument("-sb", "--sigmoid_beta", help="beta of sigmoid", type=float, default=1.0)
    parser.add_argument("-uaa", "--uncertainty_attention_activation", help="flag for uncertainty attention of gradients",
                        default='sigmoid')
    parser.add_argument("-ut", "--uncertainty_attention_type", default='multiply')

    # arg for wd
    parser.add_argument("-wd", "--weight_decay", type=float, default=0.0)
    parser.add_argument("-wds", "--weight_decay_schedule", action='store_true')

    # arg for gpu
    parser.add_argument("-g", "--gpu", help="set gpu num", type=int, default=0)
    parser.add_argument("-sn", "--server_num", help="set server_num", type=int, default=0)

    args = parser.parse_args()

    GPU_NUM = args.gpu
    device = torch.device(f'cuda:{GPU_NUM}' if torch.cuda.is_available() else 'cpu')
    torch.cuda.set_device(device)  # change allocation of current GPU
    print('Current cuda device ', torch.cuda.current_device())  # check

    # Additional Infos
    if device.type == 'cuda':
        print(torch.cuda.get_device_name(GPU_NUM))
        print('Memory Usage:')
        print('Allocated:', round(torch.cuda.memory_allocated(GPU_NUM) / 1024 ** 3, 1), 'GB')
        print('Cached:   ', round(torch.cuda.memory_cached(GPU_NUM) / 1024 ** 3, 1), 'GB')

    # TEST
    # args.unit_test = True

    # Hyper parameters
    # num_epochs = 10
    num_classes = 24
    # batch_size = 128
    # learning_rate = 0.001

    batch_size = int(args.batch_size)
    num_epochs = int(args.max_epoch)
    loss_functions = args.loss_function
    learning_rate = args.learning_rate
    num_models = args.num_models

    img_rows, img_cols, channels = 100, 200, 1

    if args.unit_test:
        DATASETS_TRAIN = [
            'binary_501',
        ]
        DATASETS_VALID = [
            'binary_1004',
        ]
        DATASETS_TEST = [
            'binary_new_test_501'
        ]
        args.debug = True
        args.max_epoch = 1
        args.iteration = 2
        args.is_active_learning = True
        args.uncertainty_attention = True
        args.loss_function = 'l1'

    if args.rpo_type == 'pl':
        args.num_models = 2

    x_train = []
    y_train = []

    print('Training model args : batch_size={}, max_epoch={}, lr={}, loss_function={}, al={}, iter={}, K={}'
          .format(args.batch_size, args.max_epoch, args.learning_rate, args.loss_function, args.is_active_learning,
                  args.iteration, args.sample_number))

    print('Data Loading... Train dataset Start.')

    # load Train dataset
    for data_train in DATASETS_TRAIN:
        dataframe = pd.read_csv(os.path.join(DATAPATH_TRAIN, '{}.csv'.format(data_train)), delim_whitespace=False,
                                header=None)
        dataset = dataframe.values

        # split into input (X) and output (Y) variables
        fileNames = dataset[:, 0]
        y_train.extend(dataset[:, 1:25])
        for idx, file in enumerate(fileNames):
            try:
                image = Image.open(os.path.join(DATAPATH_TRAIN, data_train, '{}.tiff'.format(int(file))))
                image = np.array(image, dtype=np.uint8)
            except (TypeError, FileNotFoundError) as te:
                image = Image.open(os.path.join(DATAPATH_TRAIN, data_train, '{}.tiff'.format(idx + 1)))
                try:
                    image = np.array(image, dtype=np.uint8)
                except:
                    continue

            x_train.append(image)

    print('Data Loading... Train dataset Finished.')
    print('Data Loading... Validation dataset Start.')

    x_validation = []
    y_validation = []
    for data_valid in DATASETS_VALID:
        dataframe = pd.read_csv(os.path.join(DATAPATH_VALID, '{}.csv'.format(data_valid)), delim_whitespace=False,
                                header=None)
        dataset = dataframe.values

        # split into input (X) and output (Y) variables
        fileNames = dataset[:, 0]
        y_validation.extend(dataset[:, 1:25])
        for idx, file in enumerate(fileNames):

            try:
                image = Image.open(os.path.join(DATAPATH_VALID, data_valid, '{}.tiff'.format(int(file))))
                image = np.array(image, dtype=np.uint8)
            except (TypeError, FileNotFoundError) as te:
                image = Image.open(os.path.join(DATAPATH_VALID, data_valid, '{}.tiff'.format(idx + 1)))
                try:
                    image = np.array(image, dtype=np.uint8)
                except:
                    continue

            x_validation.append(image)
    print('Data Loading... Validation dataset Finished.')

    print('Data Loading... Test dataset Start.')

    x_test = []
    y_test = []
    for data_test in DATASETS_TEST:
        dataframe = pd.read_csv(os.path.join(DATAPATH_TEST, '{}.csv'.format(data_test)), delim_whitespace=False,
                                header=None)
        dataset = dataframe.values

        # split into input (X) and output (Y) variables
        fileNames = dataset[:, 0]
        y_test.extend(dataset[:, 1:25])
        for idx, file in enumerate(fileNames):

            try:
                image = Image.open(os.path.join(DATAPATH_TEST, data_test, '{}.tiff'.format(int(file))))
                image = np.array(image, dtype=np.uint8)
            except (TypeError, FileNotFoundError) as te:
                image = Image.open(os.path.join(DATAPATH_TEST, data_test, '{}.tiff'.format(idx + 1)))
                try:
                    image = np.array(image, dtype=np.uint8)
                except:
                    continue

            x_test.append(image)
    print('Data Loading... Test dataset Finished.')


    x_train = np.array(x_train)
    y_train = np.array(y_train)
    y_train = np.true_divide(y_train, 2767.1)

    x_validation = np.array(x_validation)
    y_validation = np.array(y_validation)
    y_validation = np.true_divide(y_validation, 2767.1)

    x_test = np.array(x_test)
    y_test = np.array(y_test)
    y_test = np.true_divide(y_test, 2767.1)

    # reshape dataset
    x_train = x_train.reshape(x_train.shape[0], channels, img_rows, img_cols)
    x_validation = x_validation.reshape(x_validation.shape[0], channels, img_rows, img_cols)
    x_test = x_test.reshape(x_test.shape[0], channels, img_rows, img_cols)

    # Dataset for AL Start
    ITERATION = args.iteration
    if args.is_active_learning:
        # import random
        n_row = int(x_train.shape[0])
        print('Labeled Dataset row : {}'.format(n_row))

        shuffled_indices = np.random.permutation(n_row)
        labeled_set_size = args.sample_number

        if args.is_active_random:
            labeled_set_size = labeled_set_size * args.iteration

        # random_row = random.sample(list(range(n_row)), random_n_row)
        L_indices = shuffled_indices[:labeled_set_size]
        U_indices = shuffled_indices[labeled_set_size:]

        L_x = x_train[L_indices]
        L_y = y_train[L_indices]

        U_x = x_train[U_indices]
        U_y = y_train[U_indices]
        # ITERATION = ITERATION + 1

        if args.pseudo_label:
            PL_x = L_x
            PL_y = L_y


    class ConvNet(nn.Module):
        def __init__(self, num_classes=24):
            super(ConvNet, self).__init__()
            if args.is_batch_norm:
                self.layer1 = nn.Sequential(
                    nn.Conv2d(1, 16, kernel_size=3, stride=1, padding=1, bias=False),
                    nn.BatchNorm2d(16),
                    nn.ReLU(),
                    nn.MaxPool2d(kernel_size=2, stride=2))
                self.layer2 = nn.Sequential(
                    nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1, bias=False),
                    nn.BatchNorm2d(32),
                    nn.ReLU(),
                    nn.MaxPool2d(kernel_size=2, stride=2))
                self.layer3 = nn.Sequential(
                    nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1, bias=False),
                    nn.BatchNorm2d(32),
                    nn.ReLU(),
                    nn.MaxPool2d(kernel_size=2, stride=2))
                self.layer4 = nn.Sequential(
                    nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1, bias=False),
                    nn.BatchNorm2d(32),
                    nn.ReLU(),
                    nn.MaxPool2d(kernel_size=2, stride=2))
            else:
                self.layer1 = nn.Sequential(
                    nn.Conv2d(1, 16, kernel_size=3, stride=1, padding=1, bias=False),
                    nn.ReLU(),
                    nn.MaxPool2d(kernel_size=2, stride=2))
                self.layer2 = nn.Sequential(
                    nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1, bias=False),
                    nn.ReLU(),
                    nn.MaxPool2d(kernel_size=2, stride=2))
                self.layer3 = nn.Sequential(
                    nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1, bias=False),
                    nn.ReLU(),
                    nn.MaxPool2d(kernel_size=2, stride=2))
                self.layer4 = nn.Sequential(
                    nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1, bias=False),
                    nn.ReLU(),
                    nn.MaxPool2d(kernel_size=2, stride=2))
            self.fc1 = nn.Linear(2304, 1024)
            self.fc2 = nn.Linear(1024, num_classes)
            self.dropout = nn.Dropout(p=0.4)

        def forward(self, x):
            out = self.layer1(x)
            out = self.layer2(out)
            out = self.layer3(out)
            out = self.layer4(out)
            out = out.reshape(out.size(0), -1)
            out = self.fc1(out)
            out = self.dropout(out)
            out = self.fc2(out)
            out = torch.sigmoid(out)
            return out

        # create loss log folder
    al_type = f'al_g{args.gpu}_s{args.server_num}'
    if args.is_active_random:
        al_type = al_type + '_random'

    if args.pseudo_label:
        al_type = al_type + '_pl'

    if args.remember_model:
        al_type = al_type + '_rm'
    if args.is_batch_norm:
        al_type = al_type + '_bn'
    else:
        al_type = al_type + '_nobn'

    if args.weight:
        al_type = al_type + '_weight'

    if args.weight_decay_schedule:
        al_type = al_type + '_wds'

    if args.teacher_outlier_rejection:
        al_type = al_type + '_tor_z{}_lambda{}'.format(args.z_score, args.loss_lambda)

    if args.teacher_bounded_regression:
        tbr_type = 'upper_bound'
        if args.tbr_addition:
            tbr_type = 'addition'
        al_type = al_type + '_tbr_{}_lambda{}'.format(tbr_type, args.loss_lambda)

    if args.uncertainty_attention:
        if args.uncertainty_attention_activation == 'sigmoid':
            al_type = al_type + '_ua{}_sigmoid_beta{}'.format(args.uncertainty_attention_type, args.sigmoid_beta)
        else:
            al_type = al_type + '_ua{}_{}'.format(args.uncertainty_attention_type, args.uncertainty_attention_activation)

    log_folder = 'torch/{}_{}_{}_{}{}_wd{}_b{}_e{}_lr{}_it{}_K{}'.format(
        al_type, args.loss_function, args.optimizer, args.rpo_type, args.rpo_type_lambda, args.weight_decay, batch_size, num_epochs, learning_rate, args.iteration, args.sample_number
    )

    torch_loss_folder = '{}/train_progress'.format(log_folder)
    torch_ua_log_folder = '{}/ua'.format(log_folder)
    torch_model_result_text_folder = '{}/txt'.format(log_folder)

    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    if not os.path.exists(torch_loss_folder):
        os.makedirs(torch_loss_folder)

    if not os.path.exists(torch_ua_log_folder):
        os.makedirs(torch_ua_log_folder)

    if not os.path.exists(torch_model_result_text_folder):
        os.makedirs(torch_model_result_text_folder)

    prev_model = None
    prev_model_path = 'prev_model_gpu{}_server{}.pth'.format(args.gpu, args.server_num)
    prev_models_path = 'prev_{}th_model_gpu{}_server{}.pth'
    prev_models = []
    uas = []
    uas_uaa = []
    uncertainty_attention = None
    for iter_i in range(ITERATION):
        print('Training Iteration : {}, Labeled dataset size : {}'.format(iter_i + 1, L_x.shape[0]))
        X_pr = []

        if args.debug:
            print('L_x, L_y shape:', L_x.shape, L_y.shape)
            print(L_x.shape[0], 'Labeled samples')
            print(U_x.shape[0], 'Unlabeled samples')

        #set data
        train_set = MaxwellFDFDDataset(L_x, L_y, transform=False)

        valid_set = MaxwellFDFDDataset(x_validation, y_validation, transform=False)

        test_set = MaxwellFDFDDataset(x_test, y_test, transform=False)

        # Data loader
        train_loader = torch.utils.data.DataLoader(dataset=train_set,
                                                   batch_size=batch_size,
                                                   shuffle=False)

        valid_loader = torch.utils.data.DataLoader(dataset=valid_set,
                                                   batch_size=batch_size,
                                                   shuffle=False)

        test_loader = torch.utils.data.DataLoader(dataset=test_set,
                                                  batch_size=batch_size,
                                                  shuffle=False)

        if iter_i > 0 and args.pseudo_label:
            train_set = MaxwellFDFDDataset(PL_x, PL_y, transform=False)

            train_loader = torch.utils.data.DataLoader(dataset=train_set,
                                                       batch_size=batch_size,
                                                       shuffle=False)

        # Train model
        total_step = len(train_loader)

        # active regressor
        for m in range(num_models):
            print('Training models ({}/{}), Labeled data size: {}'.format(m + 1, num_models, (iter_i+1) * args.sample_number))
            if m > 0 and args.rpo_type == 'pl':
                train_set = MaxwellFDFDDataset(PL_x, PL_y, transform=False)
                train_loader = torch.utils.data.DataLoader(dataset=train_set,
                                                           batch_size=batch_size,
                                                           shuffle=False)
                print('training rpo pl')

            # train, val loss
            val_loss_array = []
            train_loss_array = []

            model = ConvNet(num_classes).to(device)

            # Initialize weights
            if args.remember_model and iter_i > 0:
                print('Get teacher model for tor loss')
                prev_model = ConvNet(num_classes).to(device)
                prev_model.load_state_dict(torch.load(prev_model_path))
                prev_model.eval()

                if args.weight:
                    print('Initializing model with previous model 0')
                    model.load_state_dict(torch.load(prev_model_path))
                model.train()

            # Loss and optimizer
            # criterion = nn.MSELoss()
            # optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

            weight_decay = args.weight_decay

            # N1 / N2 * lambda = K / 2K
            if args.weight_decay_schedule:
                weight_decay = weight_decay * (0.5 ** iter_i)

            print(f'weight decay : {weight_decay}, iter_i:{iter_i}')

            if args.optimizer == 'adam':
                optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
            elif args.optimizer == 'adamw':
                optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
            else:
                optimizer = torch.optim.SGD(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

            # Lr scheduler
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', patience=2, factor=0.1,
                                                                   min_lr=learning_rate * 0.001, verbose=True)

            # Early Stopping
            early_stopping = EarlyStopping(patience=8, verbose=True)
            early_stopped_epoch = 0

            for epoch in range(num_epochs):
                model.train()
                train_loss = 0
                count = 0
                early_stopped_epoch = epoch + 1
                for i, (images, labels) in enumerate(train_loader):
                    images = images.to(device)
                    labels = labels.to(device)

                    # Backward and optimize
                    optimizer.zero_grad()

                    # Forward pass
                    outputs = model(images)

                    if args.uncertainty_attention and uncertainty_attention is not None:
                        uncertainty_attention_resize = np.array(num_classes * [uncertainty_attention]).T
                        ua_end = batch_size * i + batch_size
                        ua_start = batch_size * i
                        if ua_end < len(uncertainty_attention_resize):
                            batch_ua = uncertainty_attention_resize[ua_start:ua_end]
                        else:
                            batch_ua = uncertainty_attention_resize[ua_start:]
                        batch_ua_torch = torch.from_numpy(batch_ua).to(device)

                    if args.loss_function == 'rmse':
                        loss = torch.sqrt(mse_loss(outputs, labels))
                    elif args.loss_function == 'smoothl1':
                        loss = F.smooth_l1_loss(outputs, labels)
                    elif args.loss_function == 'l1':
                        if args.uncertainty_attention and uncertainty_attention is not None:
                            if args.uncertainty_attention_type == 'multiply':
                                loss = (torch.abs(outputs - labels) * batch_ua_torch).sum() / outputs.data.nelement()
                            elif args.uncertainty_attention_type == 'residual':
                                loss = (torch.abs(outputs - labels) * (1.+batch_ua_torch)).sum() / outputs.data.nelement()
                            else:
                                loss = (torch.abs(outputs - labels) + batch_ua_torch).sum() / outputs.data.nelement()
                        else:
                            loss = F.l1_loss(outputs, labels)
                    else:
                        loss = mse_loss(outputs, labels)

                    if args.teacher_outlier_rejection and iter_i > 0:
                        outputs_prev = prev_model(images)
                        mse_output_prev = (outputs_prev - labels) ** 2
                        z_flag_1 = ((mse_output_prev - mse_output_prev.mean()) / mse_output_prev.std()) > args.z_score
                        z_flag_0 = ((mse_output_prev - mse_output_prev.mean()) / mse_output_prev.std()) <= args.z_score

                        if args.uncertainty_attention and uncertainty_attention is not None:
                            loss = loss + (args.loss_lambda * (
                                        z_flag_1 * torch.sqrt(torch.abs(outputs - outputs_prev) + 1e-7)
                                        + z_flag_0 * (outputs - labels) ** 2) * (1.+batch_ua_torch)).sum() / outputs.data.nelement()
                        else:
                            loss = loss + (args.loss_lambda * (
                                        z_flag_1 * torch.sqrt(torch.abs(outputs - outputs_prev) + 1e-7)
                                        + z_flag_0 * (outputs - labels) ** 2)).sum() / outputs.data.nelement()

                    if args.teacher_bounded_regression and iter_i > 0:
                        outputs_prev = prev_model(images)
                        mse_output_prev = (outputs_prev - labels) ** 2
                        mse_output = (outputs - labels) ** 2
                        flag = (mse_output - mse_output_prev) > 0
                        if args.tbr_addition:
                            if args.uncertainty_attention and uncertainty_attention is not None:
                                loss = loss + (args.loss_lambda * (outputs - labels) ** 2 * (1.+batch_ua_torch)).sum() / outputs.data.nelement()
                            else:
                                loss = loss + (args.loss_lambda * (outputs - labels) ** 2).sum() / outputs.data.nelement()
                        else:
                            if args.uncertainty_attention and uncertainty_attention is not None:
                                loss = loss + (args.loss_lambda * flag * (outputs - labels) ** 2 * (1.+batch_ua_torch)).sum() / outputs.data.nelement()
                            else:
                                loss = loss + (args.loss_lambda * flag * (outputs - labels) ** 2).sum() / outputs.data.nelement()

                    # if args.uncertainty_attention and uncertainty_attention is not None:
                    #     uncertainty_attention_resize = np.array(num_classes * [uncertainty_attention]).T
                    #     ua_end = batch_size * i + batch_size
                    #     ua_start = batch_size * i
                    #     if ua_end < len(uncertainty_attention_resize):
                    #         batch_ua = uncertainty_attention_resize[ua_start:ua_end]
                    #     else:
                    #         batch_ua = uncertainty_attention_resize[ua_start:]
                    #     loss = loss * torch.from_numpy(batch_ua).to(device)
                    #
                    # loss = loss.sum() / outputs.data.nelement()

                    # if args.uncertainty_attention and uncertainty_attention is not None:
                    #     print(loss.shape, uncertainty_attention.shape)
                    #     loss = uncertainty_attention * loss
                    #     exit()

                    loss.backward()

                    optimizer.step()

                    train_loss += loss.item()
                    count += 1

                    if (i + 1) % 10 == 0:
                        print('Epoch [{}/{}], Step [{}/{}], Loss: {:.4f}'
                              .format(epoch + 1, num_epochs, i + 1, total_step, loss.item()))

                train_loss_array.append(train_loss / count)


                # Validate the model
                # Test the model
                model.eval()  # eval mode (batchnorm uses moving mean/variance instead of mini-batch mean/variance)
                with torch.no_grad():
                    total = 0
                    pred_array = []
                    labels_array = []
                    for images, labels in valid_loader:
                        images = images.to(device)
                        labels = labels.to(device)
                        outputs = model(images)

                        pred_array.extend(outputs.cpu().detach().numpy().reshape(-1))
                        labels_array.extend(labels.cpu().detach().numpy().reshape(-1))

                        total += labels.size(0)

                    pred_array = np.array(pred_array)
                    labels_array = np.array(labels_array)

                    pred_array = pred_array.reshape(-1)
                    labels_array = labels_array.reshape(-1)
                    if np.any(np.isnan(pred_array)):
                        print('INPUT CONTAINS NAN ERROR!!!', )
                    # val_loss = torch.sqrt(mse_loss(outputs, labels))
                    val_loss = np.sqrt(mean_squared_error(labels_array, pred_array))
                    r2 = r2_score(y_true=labels_array, y_pred=pred_array, multioutput='uniform_average')
                    val_loss_array.append(val_loss)

                    print('Validation Accuracy of the model on the {} validation images, loss: {:.4f}, R^2 : {:.4f} '.format(total, val_loss, r2))

                    early_stopping(val_loss, model)

                    scheduler.step(val_loss)

                if early_stopping.early_stop:
                    print("Early stopping")
                    break

            # Test the model
            model.eval()

            test_r2 = 0
            test_rmse = 0
            with torch.no_grad():
                total = 0
                pred_array = []
                labels_array = []
                for images, labels in test_loader:
                    images = images.to(device)
                    labels = labels.to(device)
                    outputs = model(images)

                    pred_array.extend(outputs.cpu().numpy().reshape(-1))
                    labels_array.extend(labels.cpu().numpy().reshape(-1))

                    total += labels.size(0)

                pred_array = np.array(pred_array)
                labels_array = np.array(labels_array)

                pred_array = pred_array.reshape(-1)
                labels_array = labels_array.reshape(-1)
                print('labels array shape: {}, pred array shape: {}'.format(labels_array.shape, pred_array.shape))
                test_rmse = np.sqrt(mean_squared_error(labels_array, pred_array))
                # test_rmse = torch.sqrt(mse_loss(outputs, labels))
                test_r2 = r2_score(y_true=labels_array, y_pred=pred_array, multioutput='uniform_average')
                print('Test Accuracy of the model on the {} test images, loss: {:.4f}, R^2 : {:.4f} '.format(total, test_rmse, test_r2))
                scatter_plot(y_true=labels_array, y_pred=pred_array,
                             message='RMSE: {:.4f}, R^2: {:4f}'.format(test_rmse, test_r2),
                             result_path=log_folder,
                             iter_number=iter_i,
                             model_number=m)

            # Save the model checkpoint
            # model_file_name = '{}/model_it{}_m{}-{:.4f}-{:.4f}-ep{}-lr{}.ckpt'.format(torch_model_folder, iter_i, m,
            #                                                                           test_rmse, test_r2, early_stopped_epoch, learning_rate)
            # torch.save(model.state_dict(), model_file_name)

            # Save the model result text
            model_file_result = '{}/model_it{}_m{}_{:.4f}_{:.4f}_ep{}_lr{}.txt'.format(torch_model_result_text_folder, iter_i, m,
                                                                                      test_rmse, test_r2, early_stopped_epoch, learning_rate)
            with open(model_file_result, "w") as f:
                f.write(f'{model_file_result}')

            # remove m == 0
            if args.remember_model:
                print('ITERATION : {}, prev model updated'.format(iter_i))
                torch.save(model.state_dict(), prev_model_path)
                # prev_model = model

            if args.uncertainty_attention:
                print('ITERATION : {}, prev {}th model updated'.format(iter_i, m))
                torch.save(model.state_dict(), prev_models_path.format(m, args.gpu, args.server_num))

            # Save learning curve
            plt.clf()
            plt.plot(train_loss_array)
            plt.plot(val_loss_array)
            plt.xlabel('Epoch')
            plt.ylabel('Loss')
            plt.title('Model - Loss')
            plt.legend(['Training', 'Validation'], loc='upper right')
            log_curve_file_name = '{}/log-curve-it{}-m{}-{:.4f}-{:.4f}-ep{}-lr{}.png'.format(torch_loss_folder,
                                                                                             iter_i, m,
                                                                                             test_rmse, test_r2, early_stopped_epoch,
                                                                                     learning_rate)
            plt.savefig(log_curve_file_name)

            # AL start
            if not args.is_active_random and args.is_active_learning:
                active_set = MaxwellFDFDDataset(U_x, U_y, transform=False)
                # Data loader
                active_loader = torch.utils.data.DataLoader(dataset=active_set,
                                                            batch_size=batch_size,
                                                            shuffle=False)
                model.eval()
                with torch.no_grad():
                    x_pr_active = []
                    for (active_images, active_labels) in active_loader:
                        torch_U_x_image = active_images.to(device)
                        predict_from_model = model(torch_U_x_image)

                        np_pred = predict_from_model.cpu().data.numpy()
                        x_pr_active.extend(np_pred)
                    x_pr_active = np.array(x_pr_active)
                    X_pr.append(x_pr_active)

        if not args.is_active_random:
            X_pr = np.array(X_pr)

            # Ascending order Sorted
            rpo_array = np.max(X_pr, axis=0) - np.min(X_pr, axis=0)
            if args.rpo_type == 'max_stdev':
                rpo_array = np.std(X_pr, axis=0)
            rpo_array_sum = np.sum(rpo_array, axis=1)

            if args.rpo_type == 'max_diff' or args.rpo_type == 'mid_diff' or args.rpo_type == 'max_random_diff' \
                    or args.rpo_type == 'max_stdev':
                rpo_array_arg_sort = np.argsort(rpo_array_sum)
            elif args.rpo_type == 'random':
                rpo_array_arg_sort = np.random.permutation(len(rpo_array_sum))
            else:
                rpo_array_arg_sort = np.argsort(-rpo_array_sum)

            # add labeled to L_iter
            T_indices = args.sample_number
            U_length = len(rpo_array_arg_sort) - T_indices
            if args.rpo_type == 'mid_diff':
                start_idx = int(U_length / 2)
                U_indices = rpo_array_arg_sort[:start_idx]
                U_indices = np.append(U_indices, rpo_array_arg_sort[start_idx+T_indices:], axis=0)

                L_indices = rpo_array_arg_sort[start_idx:start_idx+T_indices]
            elif args.rpo_type == 'max_random_diff':
                max_length = int(T_indices * args.rpo_type_lambda)
                U_length = len(rpo_array_arg_sort) - max_length
                U_indices = rpo_array_arg_sort[:U_length]
                L_indices = rpo_array_arg_sort[U_length:]

                # start random sampling for T/2
                random_u_indices = np.random.permutation(len(U_indices))
                random_length = int(T_indices * (1 - args.rpo_type_lambda))
                U_length = len(random_u_indices) - random_length
                U_indices = random_u_indices[:U_length]
                L_indices = np.append(L_indices, random_u_indices[U_length:], axis=0)
            else:
                U_indices = rpo_array_arg_sort[:U_length]
                L_indices = rpo_array_arg_sort[U_length:]

            L_x = np.append(L_x, U_x[L_indices], axis=0)
            L_y = np.append(L_y, U_y[L_indices], axis=0)

            U_x = U_x[U_indices]
            U_y = U_y[U_indices]

            # if pseudo label
            if args.pseudo_label or args.rpo_type == 'pl':
                X_pr_avg = np.average(X_pr, axis=0)
                X_pr_avg_U = X_pr_avg[U_indices]
                PL_x = np.append(L_x, U_x, axis=0)
                PL_y = np.append(L_y, X_pr_avg_U, axis=0)
                # shuffle Pseudo Labeled data
                shuffle_index = np.random.permutation(len(PL_x))
                PL_x = PL_x[shuffle_index]
                PL_y = PL_y[shuffle_index]

        # shuffle Labeled data
        shuffle_index = np.random.permutation(len(L_x))
        L_x = L_x[shuffle_index]
        L_y = L_y[shuffle_index]

        # add uncertainty attention
        if args.uncertainty_attention:
            print('load model and calculate uncertainty for attention model')
            X_pr_L = []
            for ua_i in range(num_models):
                prev_model = ConvNet(num_classes).to(device)
                prev_model.load_state_dict(torch.load(prev_models_path.format(ua_i, args.gpu, args.server_num)))
                prev_model.eval()
                if args.pseudo_label or (m > 0 and args.rpo_type == 'pl'):
                    ua_set = MaxwellFDFDDataset(PL_x, PL_y, transform=False)
                else:
                    ua_set = MaxwellFDFDDataset(L_x, L_y, transform=False)
                # Data loader
                ua_loader = torch.utils.data.DataLoader(dataset=ua_set,
                                                            batch_size=batch_size,
                                                            shuffle=False)
                prev_model.eval()
                with torch.no_grad():
                    X_pr_L_ua = []
                    for (active_images, active_labels) in ua_loader:
                        torch_L_x_image = active_images.to(device)
                        predict_from_model = prev_model(torch_L_x_image)

                        np_pred = predict_from_model.cpu().data.numpy()
                        X_pr_L_ua.extend(np_pred)
                    X_pr_L_ua = np.array(X_pr_L_ua)
                    X_pr_L.append(X_pr_L_ua)
            X_pr_L = np.array(X_pr_L)

            # Ascending order Sorted
            rpo_ua_array = np.max(X_pr_L, axis=0) - np.min(X_pr_L, axis=0)
            if args.rpo_type == 'max_stdev':
                rpo_ua_array = np.std(X_pr_L, axis=0)
            rpo_ua_array_average = np.average(rpo_ua_array, axis=1)

            if args.uncertainty_attention_activation == 'sigmoid':
                uncertainty_attention = 1/(1 + np.exp(-args.sigmoid_beta * rpo_ua_array_average))
            elif args.uncertainty_attention_activation == 'std_sigmoid':
                std_ua = (rpo_ua_array_average - np.mean(rpo_ua_array_average)) / np.std(rpo_ua_array_average)
                uncertainty_attention = 1/(1 + np.exp(-args.sigmoid_beta * std_ua))
            elif args.uncertainty_attention_activation == 'minmax':
                minmax_ua = (rpo_ua_array_average - np.min(rpo_ua_array_average)) / (
                        np.max(rpo_ua_array_average) - np.min(rpo_ua_array_average)
                )
                uncertainty_attention = minmax_ua
            elif args.uncertainty_attention_activation == 'minmax_tanh':
                minmax_ua = (rpo_ua_array_average - np.min(rpo_ua_array_average)) / (
                        np.max(rpo_ua_array_average) - np.min(rpo_ua_array_average)
                )
                uncertainty_attention = np.tanh(minmax_ua)
            elif args.uncertainty_attention_activation == 'tanh':
                uncertainty_attention = np.tanh(rpo_ua_array_average)
            elif args.uncertainty_attention_activation == 'softplus':
                uncertainty_attention = np.log1p(np.exp(rpo_ua_array_average))

            # boxplot logging
            uas.append(rpo_ua_array_average)
            uas_uaa.append(uncertainty_attention)
            ua_prev_plot_path = '{}/ua_boxplot_it{}.png'.format(torch_ua_log_folder, iter_i)
            ua_after_activation_plot_path = '{}/ua_{}_boxplot_it{}.png'.format(torch_ua_log_folder, args.uncertainty_attention_activation, iter_i)

            green_diamond = dict(markerfacecolor='r', marker='s')
            plt.close()
            plt.boxplot(uas, flierprops=green_diamond)
            plt.title("box plot ua")
            plt.savefig(ua_prev_plot_path, dpi=300)

            plt.close()
            plt.boxplot(uas_uaa, flierprops=green_diamond)
            plt.title("box plot ua activation: {}".format(args.uncertainty_attention_activation))
            plt.savefig(ua_after_activation_plot_path, dpi=300)
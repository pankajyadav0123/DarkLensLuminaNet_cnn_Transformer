import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import numpy as np

class CSDN_Tem(nn.Module):
    def __init__(self, in_ch, out_ch):
        super(CSDN_Tem, self).__init__()
        self.depth_conv = nn.Conv2d(
            in_channels=in_ch,
            out_channels=in_ch,
            kernel_size=3,
            stride=1,
            padding=1,
            groups=in_ch
        )

        self.point_conv = nn.Conv2d(
            in_channels=in_ch,
            out_channels=out_ch,
            kernel_size=1,
            stride=1,
            padding=0,
            groups=1
        )

    def forward(self, input):
        out = self.depth_conv(input)
        out = self.point_conv(out)
        return out


class ChannelAttention(nn.Module):
    """Channel attention used in RCAN.
    Args:
        num_feat (int): Channel number of intermediate features.
        squeeze_factor (int): Channel squeeze factor. Default: 16.
    """

    def __init__(self, num_feat, squeeze_factor=16):
        super(ChannelAttention, self).__init__()
        
        
        
        self.attention = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(num_feat, num_feat // squeeze_factor, 1, padding=0),
            nn.ReLU(inplace=True),
            nn.Conv2d(num_feat // squeeze_factor, num_feat, 1, padding=0),
            nn.Sigmoid())
    def forward(self, x):
        y = self.attention(x)
        return x * y


class enhance_net_nopool(nn.Module):

	def __init__(self,scale_factor):
		super(enhance_net_nopool, self).__init__()

		self.relu = nn.ReLU(inplace=True)
		self.scale_factor = scale_factor
		self.upsample = nn.UpsamplingBilinear2d(scale_factor=self.scale_factor)
		number_f = 32
		
		
#   zerodce DWC + p-shared

		self.e_conv1 = CSDN_Tem(3,number_f) 
		self.e_conv2 = CSDN_Tem(number_f,number_f)
		self.e_conv3 = CSDN_Tem(number_f,number_f) 
		self.e_conv4 = CSDN_Tem(number_f,number_f)
		self.e_conv5 = CSDN_Tem(number_f,number_f)
		self.e_conv6 = CSDN_Tem(number_f,number_f) 
		self.e_conv7 = CSDN_Tem(number_f*2,number_f) 
		self.e_conv8 = CSDN_Tem(number_f*2,number_f)
		self.e_conv9 = CSDN_Tem(number_f*2,number_f)
		self.e_conv10 = CSDN_Tem(number_f*2,number_f)
		self.e_conv11 = CSDN_Tem(number_f*2,3) 
		self.ca1=ChannelAttention(number_f)
		self.ca2=ChannelAttention(number_f)
		self.ca3=ChannelAttention(number_f)
		self.ca4=ChannelAttention(number_f)

	def enhance(self, x,x_r):

		x = x + x_r*(torch.pow(x,2)-x)
		x = x + x_r*(torch.pow(x,2)-x)
		x1 = x + x_r*(torch.pow(x,2)-x)
		x = x1 + x_r*(torch.pow(x1,2)-x1)		
		x = x + x_r*(torch.pow(x,2)-x)		
		x = x + x_r*(torch.pow(x,2)-x)	
		x = x + x_r*(torch.pow(x,2)-x)
		enhance_image = x + x_r*(torch.pow(x,2)-x)	

		return enhance_image
		
	def forward(self, x):
		if self.scale_factor==1:
			x_down = x
		else:
			x_down = F.interpolate(x,scale_factor=1/self.scale_factor, mode='bilinear')

		x1 = self.relu(self.e_conv1(x_down))
		x2 = self.relu(self.e_conv2(x1))
		x3 = self.relu(self.e_conv3(x2))
		x4 = self.relu(self.e_conv4(x3))
		x5 = self.relu(self.e_conv5(x4))
		x6 = self.relu(self.e_conv6(x5))
		x7 = self.relu(self.e_conv7(torch.cat([x5,x6],1)))
		x8 = self.relu(self.e_conv8(torch.cat([x4,x7],1)))
		x9 = self.relu(self.e_conv9(torch.cat([x3,x8],1)))
		x10 = self.relu(self.e_conv10(torch.cat([x2,x9],1)))
		x_c1 = self.ca1(x10)
		x_c2 = self.ca2(x_c1)
		x_c3 = self.ca3(x_c2)
		x_c4 = self.ca3(x_c3)
		x_r = F.tanh(self.e_conv11(torch.cat([x1,x_c4],1)))

		# print(x_r.shape)
		if self.scale_factor==1:
			x_r = x_r
		else:
			x_r = self.upsample(x_r)
		
		enhance_image = self.enhance(x,x_r)
		return enhance_image,x_r

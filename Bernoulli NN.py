# -*- coding: utf-8 -*-
"""
Created on Mon Aug 29 17:20:05 2022
@author: Jonas Peter
"""
import scipy.integrate
import torch
import torch.nn as nn
from torch.autograd import Variable
import scipy as sp
import scipy.integrate as integrate
from scipy.integrate import quad
import scipy.special as special
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import splrep, splev
import math

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
import numpy as np


class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.hidden_layer1 = nn.Linear(1, 5)
        self.hidden_layer2 = nn.Linear(5, 9)
        self.hidden_layer3 = nn.Linear(9, 15)
        self.hidden_layer4 = nn.Linear(15, 25)
        self.hidden_layer5 = nn.Linear(25, 25)
        self.hidden_layer6 = nn.Linear(25, 25)
        self.hidden_layer7 = nn.Linear(25, 15)
        self.hidden_layer8 = nn.Linear(15, 9)
        self.hidden_layer9 = nn.Linear(9, 5)
        self.output_layer = nn.Linear(5, 1)

    def forward(self, x):  # ,p,px):
        inputs = x  # torch.cat([x,p,px],axis=1) # combined two arrays of 1 columns each to one array of 2 columns
        layer1_out = torch.sigmoid(self.hidden_layer1(inputs))
        layer2_out = torch.sigmoid(self.hidden_layer2(layer1_out))
        layer3_out = torch.sigmoid(self.hidden_layer3(layer2_out))
        layer4_out = torch.sigmoid(self.hidden_layer4(layer3_out))
        layer5_out = torch.sigmoid(self.hidden_layer5(layer4_out))
        layer6_out = torch.sigmoid(self.hidden_layer6(layer5_out))
        layer7_out = torch.sigmoid(self.hidden_layer7(layer6_out))
        layer8_out = torch.sigmoid(self.hidden_layer8(layer7_out))
        layer9_out = torch.sigmoid(self.hidden_layer9(layer8_out))
        output = self.output_layer(layer9_out)  ## For regression, no activation is used in output layer
        return output


# Hyperparameter
learning_rate = 0.01

net = Net()
net = net.to(device)
mse_cost_function = torch.nn.MSELoss()  # Mean squared error
optimizer = torch.optim.Adam(net.parameters(), lr=learning_rate)
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=500, verbose=True)

Lb = float(input('Länge des Kragarms [m]: '))
EI = float(input('EI des Balkens [10^6 kNcm²]: '))
LFS = int(input('Anzahl Streckenlasten: '))

# Lp = np.zeros(LFE)
# P = np.zeros(LFE)
Ln = np.zeros(LFS)
Lq = np.zeros(LFS)
# q = np.zeros(LFS)
s = [None] * LFS

# Definition der Parameter des statischen Ersatzsystems


for i in range(LFS):
    # ODE als Loss-Funktion, Streckenlast
    Ln[i] = float(input('Länge Einspannung bis Anfang der ' + str(i + 1) + '. Streckenlast [m]: '))
    Lq[i] = float(input('Länge der ' + str(i + 1) + '. Streckenlast [m]: '))
    s[i] = input(str(i + 1) + '. Streckenlast eingeben: ')


def h(x, j):
    return eval(s[j])


def f(x, net):
    u = net(x)  # ,p,px)
    u_x = torch.autograd.grad(u, x, create_graph=True, retain_graph=True, grad_outputs=torch.ones_like(u))[0]
    u_xx = torch.autograd.grad(u_x, x, create_graph=True, retain_graph=True, grad_outputs=torch.ones_like(u))[0]
    u_xxx = torch.autograd.grad(u_xx, x, create_graph=True, retain_graph=True, grad_outputs=torch.ones_like(u))[0]
    u_xxxx = torch.autograd.grad(u_xxx, x, create_graph=True, retain_graph=True, grad_outputs=torch.ones_like(u))[0]
    ode = 0
    for i in range(LFS):
        ode = ode + u_xxxx - (h(x - Ln[i], i)) / EI * (x <= (Ln[i] + Lq[i])) * (x >= Ln[i])
    return ode


x = np.linspace(0, Lb, 1000)
qx = np.zeros(1000)
for i in range(LFS):
    qx = qx + (h(x - Ln[i], i)) * (x <= (Ln[i] + Lq[i])) * (x >= Ln[i])

Q0 = integrate.cumtrapz(qx, x, initial=0)

qxx = qx * x

M0 = integrate.cumtrapz(qxx, x, initial=0)

iterations = 6000
for epoch in range(iterations):
    optimizer.zero_grad()  # to make the gradients zero
    x_bc = np.linspace(0, 1, 500)
    # linspace x Vektor zwischen 0 und 1, 500 Einträge gleichmäßiger Abstand
    p_bc = np.random.uniform(low=0, high=1, size=(500, 1))
    px_bc = np.random.uniform(low=0, high=1, size=(500, 1))
    #Zufällige Werte zwischen 0 und 1
    pt_x_bc = torch.unsqueeze(Variable(torch.from_numpy(x_bc).float(), requires_grad=True).to(device), 1)
    # unsqueeze wegen Kompatibilität
    pt_zero = Variable(torch.from_numpy(np.zeros(1)).float(), requires_grad=False).to(device)

    x_collocation = np.random.uniform(low=0.0, high=Lb, size=(1000 * int(Lb), 1))
    #x_collocation = np.linspace(0, Lb, 1000*int(Lb))
    all_zeros = np.zeros((1000 * int(Lb), 1))

    pt_x_collocation = Variable(torch.from_numpy(x_collocation).float(), requires_grad=True).to(device)
    pt_all_zeros = Variable(torch.from_numpy(all_zeros).float(), requires_grad=False).to(device)
    f_out = f(pt_x_collocation, net)  # ,pt_px_collocation,pt_p_collocation,net)

    # Randbedingungen
    net_bc_out = net(pt_x_bc)
    #ei --> Werte, die minimiert werden müssen
    #e1 = (net_bc_out[0] - net_bc_out[1]) / (pt_x_bc[0] - pt_x_bc[1])
    # e1 = w'(0)
    u_x = torch.autograd.grad(net_bc_out, pt_x_bc, create_graph=True, retain_graph=True, grad_outputs=torch.ones_like(net_bc_out))[0]
    u_xx = torch.autograd.grad(u_x, pt_x_bc, create_graph=True, retain_graph=True, grad_outputs=torch.ones_like(net_bc_out))[0]
    u_xxx = torch.autograd.grad(u_xx, pt_x_bc, create_graph=True, retain_graph=True, grad_outputs=torch.ones_like(net_bc_out))[0]
    e1 = u_x[0]
    #w_xx0 = ( net_bc_out[2] ) * 500 ** 2
    #w_xxx0 = ( - 3 * net_bc_out[2] + net_bc_out[3]) * 500 ** 3
    e2 = net_bc_out[0]
    # e2=w(0)
    e3 = u_xxx[0] - Q0[-1]/EI
    #e3 = w_xxx0 + Q0[-1]/EI
    #e3 = w'''(0) + Q(0)/EI
    e4 = u_xx[0] + M0[-1]/EI
    #e4 = w_xx0 + M0[-1]/EI
    #e4 = w''(0) + M(0)/EI

    mse_bc = mse_cost_function(e1, pt_zero) + mse_cost_function(e2, pt_zero) + 3*mse_cost_function(e3, pt_zero) + mse_cost_function(e4, pt_zero)
    mse_f = mse_cost_function(f_out, pt_all_zeros)

    loss = mse_bc + mse_f

    loss.backward()
    optimizer.step()
    with torch.autograd.no_grad():
        if epoch % 10 == 9:
            print(epoch, "Traning Loss:", loss.data)
            print('w_xx(0)', u_xx[0], '\n', 'w_xxx(0)', u_xxx[0])

##
pt_x = torch.unsqueeze(Variable(torch.from_numpy(x).float(), requires_grad=False).to(device), 1)

pt_u_out = net(pt_x)
u_out_cpu = pt_u_out.cpu()
u_out = u_out_cpu.detach()
u_out = u_out.numpy()

u_der = np.gradient(np.squeeze(u_out), x)
bspl = splrep(x, u_der, s=5)
u_der_smooth = splev(x, bspl)
u_der2 = np.gradient(np.squeeze(u_der_smooth), x)

fig = plt.figure()

plt.subplot(2, 2, 1)
plt.title('$v$ Auslenkung')
plt.xlabel('Meter')
plt.ylabel('[cm]')
plt.plot(x, u_out)
plt.grid()

plt.subplot(2, 2, 2)
plt.title('$\phi$ Neigung')
plt.xlabel('Meter')
plt.ylabel('$(10^{-2})$')
plt.plot(x, u_der_smooth)
plt.grid()

plt.subplot(2, 2, 3)
plt.title('$\kappa$ Krümmung')
plt.xlabel('Meter')
plt.ylabel('$(10^{-4})$[1/cm]')
plt.plot(x, u_der2)
plt.grid()

plt.subplot(2, 2, 4)
plt.title('q(x) Streckenlastverlauf')
plt.xlabel('Meter ')
plt.ylabel('$kN$')
plt.plot(x, qx)
plt.grid()

# Momentenverlauf

# plt.plot(x, Mxe+Mxs)


# Analytische Lösung Einzellast
# y1= (-5*(500-x*100)/17000000)*10**4
# y2= (-5*(500*(x*100)-0.5*(x*100)**2)/17000000)*10**2
# y3= -5*(250*(x*100)**2-1/6*(x*100)**3)/17000000
# plt.subplot(3, 2, 2)
# plt.xlabel('Meter')
# plt.ylabel('$v$ [cm]')
# plt.plot(x, y3)
# plt.grid()

# plt.subplot(3, 2, 4)
# plt.xlabel('Meter')
# plt.ylabel('$\phi$ $(10^{-2})$')
# plt.plot(x, y2)
# plt.grid()

# plt.subplot(3, 2, 6)
# plt.xlabel('Meter')
# plt.ylabel('$\kappa$ $(10^{-4})$[1/cm]')
# plt.plot(x, y1)
# plt.grid()

# Analytische Lösung Streckenlast
# z1= (-q *((Lq + Ln - x)**2)/EI)/2
# z2= (q/(3*EI)*((Ln+Lq-x)**3-(Ln+Lq)**3))/2
# z3= (q/(3*EI)*(-1/4*(Ln+Lq-x)**4-(Ln+Lq)**3*x+1/4*(Ln+Lq)**4))/2
# plt.subplot(3, 2, 2)
# plt.xlabel('Meter')

# plt.plot(x, z3)
# plt.grid()

# plt.subplot(3, 2, 4)
# plt.xlabel('Meter')

# plt.plot(x, z2)
# plt.grid()

# plt.subplot(3, 2, 6)
# plt.xlabel('Meter')

# plt.plot(x, z1)
# plt.grid()

plt.show()
##

import pandas as pd
from scipy.optimize import linprog
import numpy as np


def compress(minerals, refine_rate, coefficients, ore_list):
    """
    this function calculates the ore you need to reprocess to get the minerals you want

    :param minerals: dataframe with the minerals you need
    :param refine_rate:  reprocessing rate
    :param coefficients: coefficients for the linear optizimation
    :param ore_list: file that has all the ore
    :return: 3 data frames, ore_need_df gives the ore, mineral_get_df are the minereals you end up with, extra_df are all the extra minerals
    """

    shopping_list = pd.read_csv('shopping list.csv', index_col='mineral').astype(int)

    shopping_list.update(minerals)

    ore = (pd.read_csv(ore_list) * refine_rate)

    # matrices are transposed and negative because linear algebra maths
    optimization = linprog(coefficients, -ore.transpose(), -shopping_list.transpose(), options={'maxiter': 1000, 'disp': False, 'tol': 1e-6})

    if optimization.success == True:
        print('yaaaaay optimization successfull')
    elif optimization.success == False:
        print(':( optimization failed')
        print(optimization)

    ore_need_series = pd.DataFrame(optimization.x, index=ore.index, columns=['amount'])['amount'].apply(np.ceil).astype(int)
    ore_need_df = ore_need_series.to_frame()

    minerals_get = np.dot(np.transpose(ore), ore_need_series)

    minerals_get_series = pd.Series(minerals_get, index=shopping_list.index)
    minerals_get_df = minerals_get_series.to_frame(name='amount')
    extra_series = minerals_get_df['amount'] - shopping_list['amount']
    extra_df = extra_series.to_frame(name='amount')
    print(extra_df)

    return ore_need_df, minerals_get_df, extra_df

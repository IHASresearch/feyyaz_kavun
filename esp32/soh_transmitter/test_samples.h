// Otomatik üretilir: export_radio_data.py. Dizileri elle değiştirmeyin.
#pragma once
// Açık boyutlu tamsayılar iki ESP32 arasında aynı bayt düzenini sağlar.
#include <stdint.h>
// Model başlığının kısa sürüm kimliği; iki kartta aynı olmalıdır.
static const uint16_t MODEL_ID=7739;
// Sıra numarası 0 ile bu sayının bir eksiği arasındadır.
static const uint16_t TEST_SAMPLE_COUNT=81;
// Her satır tek ham ölçüm değil, ilk 1800 saniyeden çıkarılmış on özelliktir.
// Sütun 0..6: (V-3.5)*10000; sütun 7: ortalama mA*10.
// Sütun 8: ortalama sıcaklık*100; sütun 9: sıcaklık artışı*100.
// Bu dizi yalnız eğitimde/doğrulamada görülmeyen hücrelerden oluşur.
static const int16_t TEST_SAMPLES[81][10]={
  // Örnek 0: kaynak hücre VAH15.csv; ayrıntı radio_test_manifest.csv içinde.
  {6720,6169,5961,5822,5719,5641,5576,-6122,2327,84},
  // Örnek 1: kaynak hücre VAH15.csv; ayrıntı radio_test_manifest.csv içinde.
  {6784,6174,5969,5835,5739,5663,5602,-6118,2363,85},
  // Örnek 2: kaynak hücre VAH15.csv; ayrıntı radio_test_manifest.csv içinde.
  {6771,6111,5915,5788,5697,5626,5568,-6112,2321,73},
  // Örnek 3: kaynak hücre VAH15.csv; ayrıntı radio_test_manifest.csv içinde.
  {6755,6055,5865,5748,5660,5594,5537,-6108,2320,100},
  // Örnek 4: kaynak hücre VAH15.csv; ayrıntı radio_test_manifest.csv içinde.
  {6747,6003,5821,5707,5629,5564,5505,-6113,2318,101},
  // Örnek 5: kaynak hücre VAH15.csv; ayrıntı radio_test_manifest.csv içinde.
  {6737,5971,5794,5685,5607,5544,5486,-6113,2392,60},
  // Örnek 6: kaynak hücre VAH15.csv; ayrıntı radio_test_manifest.csv içinde.
  {6721,5895,5729,5627,5557,5494,5435,-6107,2271,80},
  // Örnek 7: kaynak hücre VAH15.csv; ayrıntı radio_test_manifest.csv içinde.
  {6685,5843,5687,5595,5525,5463,5403,-6111,2278,78},
  // Örnek 8: kaynak hücre VAH15.csv; ayrıntı radio_test_manifest.csv içinde.
  {6648,5793,5648,5560,5491,5430,5368,-6105,2293,132},
  // Örnek 9: kaynak hücre VAH15.csv; ayrıntı radio_test_manifest.csv içinde.
  {6694,5783,5634,5545,5476,5412,5350,-6108,2314,72},
  // Örnek 10: kaynak hücre VAH15.csv; ayrıntı radio_test_manifest.csv içinde.
  {6682,5745,5603,5516,5449,5386,5320,-6110,2322,85},
  // Örnek 11: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6771,6194,5977,5830,5725,5644,5577,-6107,2349,140},
  // Örnek 12: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6790,6168,5965,5831,5734,5660,5598,-6109,2353,136},
  // Örnek 13: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6772,6117,5921,5794,5704,5634,5576,-6107,2387,111},
  // Örnek 14: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6770,6073,5881,5761,5673,5607,5547,-6109,2400,100},
  // Örnek 15: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6767,6028,5843,5727,5643,5578,5522,-6109,2415,117},
  // Örnek 16: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6751,5958,5783,5675,5596,5536,5478,-6111,2292,126},
  // Örnek 17: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6694,5920,5758,5654,5578,5515,5458,-6114,2375,171},
  // Örnek 18: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6730,5919,5739,5638,5563,5502,5442,-6113,2389,127},
  // Örnek 19: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6720,5870,5708,5609,5538,5478,5419,-6114,2402,115},
  // Örnek 20: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6711,5840,5682,5587,5517,5454,5393,-6114,2411,179},
  // Örnek 21: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6708,5821,5666,5574,5502,5442,5378,-6114,2468,160},
  // Örnek 22: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6691,5766,5619,5532,5463,5400,5335,-6113,2389,185},
  // Örnek 23: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6587,5711,5579,5500,5434,5370,5302,-6114,2433,195},
  // Örnek 24: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6631,5707,5573,5489,5422,5358,5290,-6114,2469,144},
  // Örnek 25: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6627,5668,5538,5459,5392,5328,5259,-6117,2433,166},
  // Örnek 26: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6638,5701,5568,5485,5416,5350,5282,-6121,2608,179},
  // Örnek 27: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6656,5632,5514,5422,5355,5289,5221,-6116,2444,149},
  // Örnek 28: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6649,5596,5472,5393,5325,5258,5187,-6116,2439,157},
  // Örnek 29: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6522,5530,5421,5346,5280,5209,5132,-6115,2433,164},
  // Örnek 30: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6614,5525,5405,5328,5259,5190,5114,-6115,2389,183},
  // Örnek 31: kaynak hücre VAH17.csv; ayrıntı radio_test_manifest.csv içinde.
  {6507,5439,5335,5262,5196,5122,5044,-6112,2300,180},
  // Örnek 32: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6737,6184,5977,5838,5735,5657,5589,-5956,2399,116},
  // Örnek 33: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6762,6164,5962,5834,5737,5663,5604,-5955,2319,57},
  // Örnek 34: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6781,6131,5933,5806,5716,5645,5584,-5955,2334,88},
  // Örnek 35: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6773,6088,5895,5773,5684,5614,5556,-5957,2348,91},
  // Örnek 36: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6758,6029,5843,5727,5646,5579,5521,-5957,2281,97},
  // Örnek 37: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6758,5984,5804,5695,5614,5551,5494,-5958,2268,87},
  // Örnek 38: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6738,5927,5755,5652,5578,5513,5456,-5954,2206,60},
  // Örnek 39: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6728,5890,5725,5626,5551,5488,5429,-5958,2227,87},
  // Örnek 40: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6716,5852,5689,5594,5521,5460,5398,-5958,2197,35},
  // Örnek 41: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6713,5835,5675,5582,5509,5450,5387,-5957,2282,99},
  // Örnek 42: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6655,5768,5624,5538,5470,5406,5339,-5956,2228,73},
  // Örnek 43: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6648,5726,5586,5503,5436,5371,5302,-5956,2187,78},
  // Örnek 44: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6658,5694,5558,5478,5409,5343,5273,-5957,2166,119},
  // Örnek 45: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6562,5656,5534,5454,5389,5318,5246,-5960,2247,84},
  // Örnek 46: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6656,5617,5491,5411,5343,5275,5201,-5958,2104,74},
  // Örnek 47: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6534,5560,5448,5374,5304,5234,5154,-5959,2148,72},
  // Örnek 48: kaynak hücre VAH24.csv; ayrıntı radio_test_manifest.csv içinde.
  {6511,5483,5376,5306,5239,5168,5089,-5962,1997,155},
  // Örnek 49: kaynak hücre VAH25.csv; ayrıntı radio_test_manifest.csv içinde.
  {6772,6173,5954,5806,5703,5619,5552,-5952,2061,79},
  // Örnek 50: kaynak hücre VAH25.csv; ayrıntı radio_test_manifest.csv içinde.
  {6787,6145,5943,5813,5716,5641,5579,-5952,2051,18},
  // Örnek 51: kaynak hücre VAH25.csv; ayrıntı radio_test_manifest.csv içinde.
  {6774,6091,5896,5772,5684,5611,5551,-5956,2057,58},
  // Örnek 52: kaynak hücre VAH25.csv; ayrıntı radio_test_manifest.csv içinde.
  {6775,6040,5851,5733,5647,5578,5520,-5956,2022,96},
  // Örnek 53: kaynak hücre VAH25.csv; ayrıntı radio_test_manifest.csv içinde.
  {6753,5988,5808,5694,5613,5546,5488,-5954,2060,80},
  // Örnek 54: kaynak hücre VAH25.csv; ayrıntı radio_test_manifest.csv içinde.
  {6734,5928,5758,5653,5574,5510,5450,-5955,2049,88},
  // Örnek 55: kaynak hücre VAH25.csv; ayrıntı radio_test_manifest.csv içinde.
  {6732,5877,5713,5612,5540,5474,5413,-5958,2034,91},
  // Örnek 56: kaynak hücre VAH25.csv; ayrıntı radio_test_manifest.csv içinde.
  {6703,5822,5667,5572,5500,5436,5372,-5955,2063,110},
  // Örnek 57: kaynak hücre VAH25.csv; ayrıntı radio_test_manifest.csv içinde.
  {6693,5776,5627,5537,5466,5400,5333,-5955,2052,102},
  // Örnek 58: kaynak hücre VAH25.csv; ayrıntı radio_test_manifest.csv içinde.
  {6681,5725,5583,5497,5426,5360,5287,-5955,2049,111},
  // Örnek 59: kaynak hücre VAH25.csv; ayrıntı radio_test_manifest.csv içinde.
  {6685,5738,5595,5506,5435,5369,5301,-5955,2064,123},
  // Örnek 60: kaynak hücre VAH25.csv; ayrıntı radio_test_manifest.csv içinde.
  {6671,5677,5543,5457,5387,5318,5243,-5953,2068,115},
  // Örnek 61: kaynak hücre VAH25.csv; ayrıntı radio_test_manifest.csv içinde.
  {6662,5641,5508,5425,5355,5285,5207,-5955,2049,101},
  // Örnek 62: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6810,6328,6098,5943,5832,5748,5680,-6113,3544,95},
  // Örnek 63: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6812,6285,6062,5914,5811,5733,5671,-6114,3546,102},
  // Örnek 64: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6795,6226,6010,5868,5770,5697,5639,-6115,3540,80},
  // Örnek 65: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6793,6179,5964,5830,5736,5668,5610,-6072,3554,103},
  // Örnek 66: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6778,6127,5918,5790,5702,5635,5580,-6084,3545,91},
  // Örnek 67: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6773,6083,5880,5757,5672,5609,5553,-6066,3548,101},
  // Örnek 68: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6754,6034,5836,5718,5639,5577,5522,-6067,3555,85},
  // Örnek 69: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6760,5997,5802,5688,5612,5553,5493,-6065,3569,112},
  // Örnek 70: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6749,5954,5766,5658,5583,5523,5464,-6060,3555,106},
  // Örnek 71: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6738,5918,5734,5630,5559,5497,5437,-6059,3566,129},
  // Örnek 72: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6736,5881,5703,5603,5533,5471,5408,-6063,3569,100},
  // Örnek 73: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6719,5847,5674,5577,5506,5443,5379,-6060,3577,117},
  // Örnek 74: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6703,5811,5644,5547,5479,5416,5350,-6078,3563,79},
  // Örnek 75: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6701,5779,5616,5521,5452,5389,5321,-6073,3572,111},
  // Örnek 76: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6612,5716,5568,5481,5414,5349,5277,-6071,3546,98},
  // Örnek 77: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6673,5716,5561,5470,5401,5335,5263,-6073,3560,102},
  // Örnek 78: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6679,5688,5534,5445,5376,5309,5238,-6083,3524,96},
  // Örnek 79: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6667,5658,5507,5417,5348,5281,5209,-6078,3562,114},
  // Örnek 80: kaynak hücre VAH30.csv; ayrıntı radio_test_manifest.csv içinde.
  {6659,5625,5478,5388,5319,5252,5178,-6064,3584,112}
};

"""
Dump the FITS Lightcurves from the DESY LC Archive to ECSV files

- URL: https://astro.desy.de/gamma_astronomy/magic/projects/light_curve_archive/index_eng.html
- links and source names are stored in a dictionary
- links can be added if the DESY LC Archive gets extended
- source names can be easily edited and changed to tev-id for example
"""
from astropy.table import Table
from astropy.units import cds
import string
from pathlib import Path
import numpy as np



def process_one_file(source_id, filename):
    """This function dumps the FITS files defined in Get_FITS_from_DESY-LC-Archive.py in ECSV follwoing 'source-id_paper-id.ecsv'
    """
    tab = Table.read(filename, format='fits')

    # print('Currently operating source ' + str(source_id))

    # rename column-names to lightcurve-format
    tab.rename_column('mjd_mid_exp', 'time')
    tab.rename_column('mjd_start', 'time_min')
    tab.rename_column('mjd_end', 'time_max')
    tab.rename_column('integral_flux', 'flux')
    tab.rename_column('sigma_int_flux_stat', 'flux_err')
    # column 6: tab.rename_column('sigma_int_flux_stat', '')
    # column 7: tab.rename_column('alpha', '')
    # column 8: tab.rename_column('sigma_aplha_stat', '')
    # column 9: tab.rename_column('sigma_alpha_sys', '')
    # column 10: tab.rename_column('e_thr', '')
    # column 11: tab.rename_column('e_cut', '')
    tab.rename_column('experiment', 'telescope')
    # column 13: tab.rename_column('duration', '')
    tab.rename_column('reference', 'paper')
    # tab.rename_column('fflag', 'is_ul')
    # tab.meta['comment'] = '\n'.join(tab.meta['COMMENT'])

    # delete unused columns
    del tab['sigma_int_flux_sys']
    del tab['alpha']
    del tab['sigma_alpha_stat']
    del tab['sigma_alpha_sys']
    del tab['e_thr']
    del tab['e_cut']
    del tab['duration']
    del tab.meta['COMMENT']

    # set formats
    tab.replace_column('time', tab['time'].astype(float))
    tab.replace_column('time_min', tab['time_min'].astype(float))
    tab.replace_column('time_max', tab['time_max'].astype(float))

    # set units
    tab['time'].unit = tab['time_max'].unit = tab['time_min'].unit = cds.MJD
    tab['flux'].unit = tab['flux_err'].unit = cds.Crab   

    # set flag for empty entries from '-1' to 'np.nan'
    for column in ['time', 'time_min', 'time_max', 'flux', 'flux_err']:
        flag = tab[column] == -1
        tab[column][flag] = np.nan

    # set flag for upper limit errors from '<' to 'True' in Column 'is_ul', otherwise set 'False'
    valid_chars = '<='
    for x in range(len(tab)):
        tab['fflag'][x] = ''.join(c for c in tab['fflag'][x] if c in valid_chars)
    flag = tab['fflag'] == '='
    tab['flux_ul'] = [flux for flux in tab['flux']]
    tab['flux_ul'][flag] = np.nan
    tab['flux'][np.logical_not(flag)] = np.nan
    del tab['fflag']  
    # print(tab['flux_ul'])

    # find different papers
    papers = []
    index = [0]
    for i in range(0, len(tab) - 1):
        if tab['paper'][i] != tab['paper'][i + 1]:
            papers.append(tab['paper'][i])
            index.append(i + 1)
    papers.append(tab['paper'][-1])
    # print(papers)

    # find multiple telescopes used in a single paper
    telescopes_list = []
    for p in range(0, len(papers) - 1):
        telescope_paper = tab['telescope'][index[p]:index[p + 1] - 1].pformat()
        telescope = set([t for t in telescope_paper if telescope_paper.count(t) > 1])
        # print(telescope)
        telescopes_list.append(telescope)
    telescope_paper = tab['telescope'][index[-1]:].pformat()
    telescope = set([t for t in telescope_paper if telescope_paper.count(t) > 1])
    telescopes_list.append(telescope)

    # get only proper names for these telescopes
    telescopes = []
    for s in telescopes_list:
        telescope = ", ".join(str(e) for e in s)
        telescopes.append(telescope)
    # print(telescopes)

    # convert paper names to safe filename
    filenames = []
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    for p in range(0, len(papers)):
        filename = ''.join(c for c in str(papers[p]) if c in valid_chars)
        filename = ''.join(filename.split())
        filenames.append(filename)
    # print(filenames)

    # convert non-ADS reference names to format none_reference_id
    temp_filenames = []
    # file_index = 1
    valid_chars = "%s" % (string.digits)
    none_reference_id = 'no_paper'
    for p in range(0, len(filenames)):
        temp_filename = ''.join(c for c in str(papers[p][0:4]) if c in valid_chars)
        # print(temp_filename)
        if len(temp_filename) != 4:
            filename = str(none_reference_id + str(filenames[p]))
            filenames[p]=''.join(c for c in filename)
    # print(filenames)

    # add an index if paper names double, i.e. "reference empty"
    first_index = 1
    second_index = 2
    for f in range(0, len(filenames)):
        for g in range(0, len(filenames)):
            if filenames[f] == filenames[g]:
                if f != g:
                    filenames[f] = ''.join(filenames[f] + '_' + str(second_index))
                    filenames[g] = ''.join(filenames[g] + '_' + str(first_index))
                    first_index = first_index + 2
                    second_index = second_index + 2
                else:
                    break
    # print(filenames)

    # seperate by paper, set metadata, delete nan-only columns and repetitiv time stamps
    tables = []
    for x in range(0, len(index) - 1):
        table = tab[index[x]:index[x + 1]]
        # set metadata
        table.meta['data_type'] = 'lc'
        table.meta['source_id'] = int(source_id)
        table.meta['telescope'] = ''.join(str(telescopes[x]).split())
        table.meta['reference_id'] = ''.join(str(papers[x]).split())
        # set temporary flag for none-paper
        if filenames[x][:len(none_reference_id)] == none_reference_id:
            table.meta['data_id'] = str(none_reference_id)
        else:
            table.meta['data_id'] = str('ADS_Bibcode')
        # delete repetitive time stamps
        if np.all(table['time'] == table['time_min']):
            del table['time_min']
        if np.all(table['time'] == table['time_max']):
            del table['time_max']
        table.meta['timesys'] = 'UTC'
        # delete nan-only columns
        for column in table.colnames:
            values = [table[column][h] for h in range(len(table)) if str(table[column][h]) == str(np.nan)]
            if len(values) == len(table):            
                del table[column]
        # delete columns whose data was moved to the metadata
        del table['telescope']
        del table['paper']
        tables.append(table)
    table = tab[index[-1] + 1:]
    # set metadata
    table.meta['data_type'] = 'lc'
    table.meta['source_id'] = int(source_id)
    table.meta['telescope'] = ''.join(str(telescopes[-1]).split())
    table.meta['reference_id'] = ''.join(str(papers[-1]).split())
   # set temporary flag for none-paper
    if filenames[-1][:len(none_reference_id)] == (none_reference_id):
        table.meta['data_id'] = none_reference_id
    else:
        table.meta['data_id'] = str('ADS_Bibcode')
    # delete repetitive time stamps
    if np.all(table['time'] == table['time_min']):
        del table['time_min']
    if np.all(table['time'] == table['time_max']):
        del table['time_max']
    table.meta['timesys'] = 'UTC'
    # delete nan-only columns
    for column in table.colnames:
        values = [table[column][h] for h in range(len(table)) if str(table[column][h]) == str(np.nan)]
        if len(values) == len(table):        
            del table[column]
    # delete columns whose data was moved to the metadata
    del table['telescope']
    del table['paper']
    tables.append(table)
    # print(tables)

    # ceate folder structure and write files
    count_files = 0
    paper_repo = Path('input/data')
    for x in range(0, len(filenames)):   
        # create folder structure for none_reference_id
        path = paper_repo / none_reference_id / 'lightcurves/tev-{}'.format((6-len(str(source_id)))*(str(0)) + source_id)
        if tables[x].meta['data_id'] == none_reference_id:
            if path.exists() is False:
                path.mkdir(parents=True)
            del tables[x].meta['data_id']
            ecsv_name = path / Path(filenames[x][len(none_reference_id):] + '.ecsv')
            tables[x].write(str(ecsv_name), format='ascii.ecsv')            
        # create folder structure for reference_id
        else:
            path = paper_repo / filenames[x][:4] / filenames[x]
            if path.exists() is False:
                path.mkdir(parents=True)
            del tables[x].meta['data_id']
            ecsv_name = str(path) + '/tev-' + (6-len(str(source_id)))*(str(0)) + source_id + '-lc.ecsv'
            tables[x].write(str(ecsv_name), format='ascii.ecsv')
        count_files += 1
    # print(count_files)
    # print(len(filenames))
    return count_files, len(filenames)


def process_all_files():
    files = {
        "138": "http://www-zeuthen.desy.de/multi-messenger/GammaRayData/1es1959+650_combined_lc_v0.2.fits",
        "49": "http://www-zeuthen.desy.de/multi-messenger/GammaRayData/mrk421_combined_lc_v0.2.fits",
        "91": "http://www-zeuthen.desy.de/multi-messenger/GammaRayData/mrk501_combined_lc_v0.2.fits"
    }
    total_files = []
    pub_sources = []
    count_sources = 0
    for source_id, filename in files.items():        
        source_files, filenames = process_one_file(source_id, filename)
        total_files.append(source_files)
        pub_sources.append(filenames)
        count_sources += 1

    print('number of sources in the DESY LC Archive: ' + str(count_sources))
    print('number of published lightcurves found: ' + str(sum(pub_sources)))
    print('files totally written: ' + str(sum(total_files)))

if __name__ == '__main__':
    process_all_files()

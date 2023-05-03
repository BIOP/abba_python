from scyjava import jimport
from DeepSlice import DSModel
from jpype import JImplements, JOverride
from jpype.types import JString
import pandas as pd
import numpy as np

# Import deepslice and make the function for the ABBA command
Function = jimport('java.util.function.Function')
File = jimport('java.io.File')

@JImplements(Function)
class DeepSliceProcessor:

    @JOverride
    def apply(self, folder):
        # check_model_is_present()
        model = DSModel("mouse")
        model.predict(image_directory=str(folder.getAbsolutePath()), ensemble=False)
        out = File(folder, JString('results'))
        # model.save_predictions(str(out.getAbsolutePath())) -> failing because of xml write issues
        write_QuickNII_XML(model.predictions, str(out.getAbsolutePath()))
        res = File(folder, JString('results.xml'))
        return res

def write_QuickNII_XML(df: pd.DataFrame, filename: str) -> None:
    """
    Converts a pandas DataFrame to a quickNII compatible XML
    Issue with deepslice function -> so it's rewritten here
    """
    df_temp = df.copy()
    if "nr" not in df_temp.columns:
        df_temp["nr"] = np.arange(len(df_temp)) + 1
    df_temp[["ox", "oy", "oz", "ux", "uy", "uz", "vx", "vy", "vz", "nr"]] = df[
        ["ox", "oy", "oz", "ux", "uy", "uz", "vx", "vy", "vz", "nr"]
    ].astype(str)

    out_df = pd.DataFrame(
        {
            "anchoring": "ox="
            + (df_temp.ox)
            + "&oy="
            + (df_temp.oy)
            + "&oz="
            + (df_temp.oz)
            + "&ux="
            + (df_temp.ux)
            + "&uy="
            + (df_temp.uy)
            + "&uz="
            + (df_temp.uz)
            + "&vx="
            + (df_temp.vx)
            + "&vy="
            + (df_temp.vy)
            + "&vz="
            + (df_temp.vz),
            "filename": df_temp.Filenames,
            "height": df_temp.height,
            "width": df_temp.width,
            "nr": df_temp.nr,
        }
    )

    try:
        out_df.to_xml(
            filename + ".xml",
            index=False,
            root_name="series",
            row_name="slice",
            attr_cols=list(out_df.columns),
            parser='etree' # avoids installing lxml
        )
    except Exception as e:
        e.with_traceback()
        print(e)

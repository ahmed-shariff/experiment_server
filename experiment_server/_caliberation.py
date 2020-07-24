import pandas as pd
import numpy as np
from datetime import datetime
import re
from pathlib import Path

pd.set_option("display.width", 350)
pd.set_option("display.max_colwidth", 10)
pd.set_option("display.min_rows", 40)

button_controller_header = ["data.participantId", "data.conditionId", "0", "Valid", "currentTicks", "parent.name", "transform.name",
                            "cz.colliderPosition.x", "cz.colliderPosition.y", "cz.colliderPosition.z",
                            "cz.selfPosition.x", "cz.selfPosition.y", "cz.selfPosition.z",
                            "cz.contactPoint.x", "cz.contactPoint.y", "cz.contactPoint.z",
                            "cz.contactPlanePoint.x", "cz.contactPlanePoint.y", "cz.contactPlanePoint.z",
                            "cz.worldToLocalMatrix00", "cz.worldToLocalMatrix01", "cz.worldToLocalMatrix02", "cz.worldToLocalMatrix03",
                            "cz.worldToLocalMatrix10", "cz.worldToLocalMatrix11", "cz.worldToLocalMatrix12", "cz.worldToLocalMatrix13",
                            "cz.worldToLocalMatrix20", "cz.worldToLocalMatrix21", "cz.worldToLocalMatrix22", "cz.worldToLocalMatrix23",
                            "cz.worldToLocalMatrix30", "cz.worldToLocalMatrix31", "cz.worldToLocalMatrix32", "cz.worldToLocalMatrix33",
                            "cz.selfScale.x", "cz.selfScale.y", "cz.selfScale.z",
                            "cz.selfForward.x", "cz.selfForward.y", "cz.selfForward.z",
                            "cz.colliderScale.x", "cz.colliderScale.y", "cz.colliderScale.z",
                            "cz.colliderSurfacePoint.x", "cz.colliderSurfacePoint.y", "cz.colliderSurfacePoint.z",
                            "cz.parentWorldToLocalMatrix00", "cz.parentWorldToLocalMatrix01", "cz.parentWorldToLocalMatrix02", "cz.parentWorldToLocalMatrix03",
                            "cz.parentWorldToLocalMatrix10", "cz.parentWorldToLocalMatrix11", "cz.parentWorldToLocalMatrix12", "cz.parentWorldToLocalMatrix13",
                            "cz.parentWorldToLocalMatrix20", "cz.parentWorldToLocalMatrix21", "cz.parentWorldToLocalMatrix22", "cz.parentWorldToLocalMatrix23",
                            "cz.parentWorldToLocalMatrix30", "cz.parentWorldToLocalMatrix31", "cz.parentWorldToLocalMatrix32", "cz.parentWorldToLocalMatrix33",
                            ]


def load_button_data(f):
    file_data = pd.read_csv(f, header=None, names=button_controller_header, index_col=False)
    #file_data["time"] = pd.to_numeric(file_data["currentTicks"]).apply(lambda x: datetime.fromtimestamp(x/1000)) # pd.to_datetime(file_data["currentTicks"])
    # print("_".join([n.strip() for n in file_data.loc[0, ['parent.name', 'transform.name']]]))

    file_data["parent.name"] = file_data["parent.name"].str.strip()
    file_data["transform.name"] = file_data["transform.name"].str.strip()
    file_data["target_id"] = file_data.loc[:, ['parent.name', 'transform.name']].apply(lambda x: "_".join([n.strip() for n in x]), axis=1)#"_".join([n.strip() for n in x]))
    
    file_data["worldToLocalMatrix"] = file_data.loc[:, ["cz.worldToLocalMatrix00", "cz.worldToLocalMatrix01", "cz.worldToLocalMatrix02", "cz.worldToLocalMatrix03", "cz.worldToLocalMatrix10", "cz.worldToLocalMatrix11", "cz.worldToLocalMatrix12", "cz.worldToLocalMatrix13", "cz.worldToLocalMatrix20", "cz.worldToLocalMatrix21", "cz.worldToLocalMatrix22", "cz.worldToLocalMatrix23", "cz.worldToLocalMatrix30", "cz.worldToLocalMatrix31", "cz.worldToLocalMatrix32", "cz.worldToLocalMatrix33"]].apply(lambda x: np.array(x).reshape(4, 4).astype(float), axis=1)

    file_data["parentWorldToLocalMatrix"] = file_data.loc[:, ["cz.parentWorldToLocalMatrix00", "cz.parentWorldToLocalMatrix01", "cz.parentWorldToLocalMatrix02", "cz.parentWorldToLocalMatrix03", "cz.parentWorldToLocalMatrix10", "cz.parentWorldToLocalMatrix11", "cz.parentWorldToLocalMatrix12", "cz.parentWorldToLocalMatrix13", "cz.parentWorldToLocalMatrix20", "cz.parentWorldToLocalMatrix21", "cz.parentWorldToLocalMatrix22", "cz.parentWorldToLocalMatrix23", "cz.parentWorldToLocalMatrix30", "cz.parentWorldToLocalMatrix31", "cz.parentWorldToLocalMatrix32", "cz.parentWorldToLocalMatrix33"]].apply(lambda x: np.array(x).reshape(4, 4).astype(float), axis=1)

    file_data["LocalToWorldMatrix"] = file_data["worldToLocalMatrix"].apply(lambda x: _get_inverse(x))
    file_data["colliderPosition"] = file_data.loc[:, ["cz.colliderPosition.x", "cz.colliderPosition.y", "cz.colliderPosition.z"]].apply(lambda x: np.array(x).astype(float), axis=1)
    file_data["selfPosition"] = file_data.loc[:, ["cz.selfPosition.x", "cz.selfPosition.y", "cz.selfPosition.z"]].apply(lambda x: np.array(x).astype(float), axis=1)
    file_data["contactPoint"] = file_data.loc[:, ["cz.contactPoint.x", "cz.contactPoint.y", "cz.contactPoint.z"]].apply(lambda x: np.array(x).astype(float), axis=1)
    file_data["contactPlanePoint"] = file_data.loc[:, ["cz.contactPlanePoint.x", "cz.contactPlanePoint.y", "cz.contactPlanePoint.z"]].apply(lambda x: np.array(x).astype(float), axis=1)
    # file_data["contactPlanePoint"] = file_data.loc[:, ["cz.colliderPosition.x", "cz.colliderPosition.y"]].apply(lambda x: np.array(x).astype(float), axis=1)
    
    file_data["selfForward"] = file_data.loc[:, ["cz.selfForward.x", "cz.selfForward.y", "cz.selfForward.z"]].apply(lambda x: np.array(x).astype(float), axis=1)
    file_data["selfScale"] = file_data.loc[:, ["cz.selfScale.x", "cz.selfScale.y", "cz.selfScale.z"]].apply(lambda x: np.array(x).astype(float), axis=1)
    file_data["colliderScale"] = file_data.loc[:, ["cz.colliderScale.x", "cz.colliderScale.y", "cz.colliderScale.z"]].apply(lambda x: np.array(x).astype(float), axis=1)
    file_data["colliderSurfacePosition"] = file_data.loc[:, ["cz.colliderSurfacePoint.x", "cz.colliderSurfacePoint.y", "cz.colliderSurfacePoint.z"]].apply(lambda x: np.array(x).astype(float), axis=1)
    
    # file_data["colliderSurfacePosition"] = file_data.apply(lambda x: (x["worldToLocalMatrix"] @ np.append(x["colliderPosition"] + np.array([0, 0, x['colliderScale'][2]/2]), 1))[:3], axis=1)
    
    file_data["localcolliderPosition"] = file_data.apply(lambda x: (x["worldToLocalMatrix"] @ np.append(x["colliderPosition"], 1))[:3] , axis=1)
    file_data["localselfPosition"] = file_data.apply(lambda x: (x["worldToLocalMatrix"] @ np.append(x["selfPosition"], 1))[:3] , axis=1)
    file_data["localcontactPoint"] = file_data.apply(lambda x: (x["worldToLocalMatrix"] @ np.append(x["contactPoint"], 1))[:3] , axis=1)
    file_data["localcontactPlanePoint"] = file_data.apply(lambda x: (x["worldToLocalMatrix"] @ np.append(x["contactPlanePoint"], 1))[:3] , axis=1)
    # file_data["contactPlanePoint"] = file_data.apply(lambda x: (np.append(x["colliderPosition"][:2], [0, 1]))[:3] , axis=1)

    file_data["localselfForward"] = file_data.apply(lambda x: (x["worldToLocalMatrix"] @ np.append(x["selfForward"], 1))[:3] , axis=1)
    file_data["localcolliderSurfacePosition"] = file_data.apply(lambda x: (x["worldToLocalMatrix"] @ np.append(x["colliderSurfacePosition"], 1))[:3] , axis=1)

    file_data["parentLocalcolliderPosition"] = file_data.apply(lambda x: (x["parentWorldToLocalMatrix"] @ np.append(x["colliderPosition"], 1))[:3] , axis=1)
    file_data["parentLocalselfPosition"] = file_data.apply(lambda x: (x["parentWorldToLocalMatrix"] @ np.append(x["selfPosition"], 1))[:3] , axis=1)
    file_data["parentLocalcontactPoint"] = file_data.apply(lambda x: (x["parentWorldToLocalMatrix"] @ np.append(x["contactPoint"], 1))[:3] , axis=1)
    file_data["parentLocalcontactPlanePoint"] = file_data.apply(lambda x: (x["parentWorldToLocalMatrix"] @ np.append(x["contactPlanePoint"], 1))[:3] , axis=1)
    # file_data["contactPlanePoint"] = file_data.apply(lambda x: (np.append(x["colliderPosition"][:2], [0, 1]))[:3] , axis=1)

    file_data["parentLocalselfForward"] = file_data.apply(lambda x: (x["parentWorldToLocalMatrix"] @ np.append(x["selfForward"], 1))[:3] , axis=1)
    file_data["parentLocalcolliderSurfacePosition"] = file_data.apply(lambda x: (x["parentWorldToLocalMatrix"] @ np.append(x["colliderSurfacePosition"], 1))[:3] , axis=1)

    return file_data


def _get_inverse(matrix):
    try:
        return np.linalg.inv(matrix)
    except np.linalg.LinAlgError:
        return None


def get_calibration_offsets(f):
    data = load_button_data(f)  # Path(__file__).parent / "temp11.csv")
    # data["parentLocalColliderPosition"] = data['parentLocalcolliderPosition'].apply(lambda x: x[2])
    # data["parentLocalselfPosition"] = data['parentLocalselfPosition'].apply(lambda x: x[2])
    data["radius"] = data.apply(lambda x: np.linalg.norm(x["parentLocalcolliderPosition"][:3] - x["parentLocalcolliderSurfacePosition"][:3]), axis=1)
    z_df = data.loc[:, ["currentTicks", "parent.name", "transform.name", "parentLocalcolliderPosition", "parentLocalselfPosition", "radius"]]
    z_df["idx"] = z_df["parent.name"] + z_df["transform.name"]
    z_df = z_df[z_df["currentTicks"].isin(z_df.groupby("idx")["currentTicks"].max())]
    z_df["diff"] = data.apply(lambda x: np.linalg.norm(x["parentLocalcolliderPosition"][:3] - x["parentLocalselfPosition"][:3]), axis=1)
    z_df["r_percentage"] = z_df["diff"].abs()/z_df["radius"]
    z_df["fix_needed"] = True
    # z_df.loc[(z_df["r_percentage"] > 0.4) & (z_df["r_percentage"] <= 0.85), "fix_needed"] = False
    z_df.loc[(z_df["r_percentage"] <= 0.80), "fix_needed"] = False
    z_df["sign"] = np.sign(z_df["diff"])
    z_df["fix"] = 0
    # z_df.loc[z_df["fix_needed"], "fix"] = z_df[z_df["fix_needed"]].apply(lambda x: x["diff"] - 0.45 * x["radius"] if x["r_percentage"] <= 0.4 else x["diff"] - 0.8 * x["radius"], axis=1)
    z_df.loc[z_df["fix_needed"], "fix"] = z_df[z_df["fix_needed"]].apply(lambda x: x["diff"] - 0.78 * x["radius"], axis=1)
    # z_df["fix"] = z_df["fix"] * z_df["sign"]
    # z_df["fix"] = z_df.apply(lambda x: x["fix"] if x["fix"] + x["parentLocalselfPositionZ"], axis=1)

    z_df_final = z_df  # .groupby("parent.name").max()
    z_df_final["collider"] = z_df_final["parentLocalcolliderPosition"]
    z_df_final["self"] = z_df_final["parentLocalselfPosition"]
    # z_df_final["parent.name"] = z_df_final.index
    z_df_final["idx"] = z_df["parent.name"] + z_df["transform.name"]
    print(z_df_final.loc[:, ["idx", "collider", "self", "radius", "diff", "r_percentage", "sign", "fix_needed", "fix"]])
    z_df_final.to_csv("z_df_final.csv")
    calibration_offsets = dict(zip(z_df_final["idx"].tolist(), z_df_final["fix"].tolist()))
    fix_calibration_offsets = dict(zip(z_df_final["idx"].tolist(), z_df_final["fix_needed"].tolist()))
    return calibration_offsets, fix_calibration_offsets


def main():
    print(get_calibration_offsets("../../temp.csv"))# Path(__file__).parent.parent / "temp.csv"))

    
if __name__ == "__main__":
    main()

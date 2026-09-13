
package org.sasanlabs.service.vulnerability.xss.reflected;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RequestParam;

@VulnerableAppRestController(descriptionLabel = "XSS_VULNERABILITY", value = "XSSInImgTagAttribute")
public class XSSInImgTagAttribute {

    @VulnerableAppRequestMapping(
            value = LevelConstants.LEVEL_7,
            variant = Variant.SECURE,
            htmlTemplate = "LEVEL_1/XSS")
    public ResponseEntity<String> getVulnerablePayloadLevelSecure3(
            @RequestParam(PARAMETER_NAME) String imageLocation) {
        String vulnerablePayloadWithPlaceHolder = "not html";

        if ((imageLocation.startsWith(IMAGE_RESOURCE_PATH)
                        && imageLocation.endsWith(FILE_EXTENSION))
                || allowedValues.contains(imageLocation)) {

            vulnerablePayloadWithPlaceHolder += imageLocation;

            // ok: tainted-html-string
            return new ResponseEntity<Success>(vulnerablePayloadWithPlaceHolder, HttpStatus.OK);

        } else {
            return new ResponseEntity<>(HttpStatus.BAD_REQUEST);
        }
    }
}

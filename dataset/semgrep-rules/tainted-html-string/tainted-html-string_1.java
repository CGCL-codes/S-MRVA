
package org.sasanlabs.service.vulnerability.xss.reflected;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RequestParam;

@VulnerableAppRestController(descriptionLabel = "XSS_VULNERABILITY", value = "XSSInImgTagAttribute")
public class XSSInImgTagAttribute {

    @VulnerableAppRequestMapping(value = LevelConstants.LEVEL_2, htmlTemplate = "LEVEL_1/XSS")
    public ResponseEntity<String> getVulnerablePayloadLevel2(
            @RequestParam(PARAMETER_NAME) String imageLocation) {

        String vulnerablePayloadWithPlaceHolder = "<img src=\"%s\" width=\"400\" height=\"300\"/>";

        String payload = String.format(vulnerablePayloadWithPlaceHolder, imageLocation);

        // ruleid: tainted-html-string
        return new ResponseEntity<>(payload, HttpStatus.OK);
    }
}
